"""Add immutable Phase 5 evaluation artifacts and research gates.

Revision ID: 0005_phase5
Revises: 0004_phase4
Create Date: 2026-07-14 04:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase5"
down_revision: str | None = "0004_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PHASE5_TABLES = (
    "evaluation_policies",
    "evaluation_feature_specs",
    "evaluation_label_specs",
    "evaluation_blocked_outcomes",
    "evaluation_reports",
    "evaluation_report_snapshots",
    "evaluation_trials",
    "evaluation_folds",
    "evaluation_preprocessing_fits",
    "evaluation_oos_ledger",
    "evaluation_cost_ledger",
    "evaluation_gate_results",
)

PHASE5_POLICY_CHILD_TABLES = (
    "evaluation_feature_specs",
    "evaluation_label_specs",
)

PHASE5_REPORT_CHILD_TABLES = (
    "evaluation_report_snapshots",
    "evaluation_trials",
    "evaluation_folds",
    "evaluation_preprocessing_fits",
    "evaluation_oos_ledger",
    "evaluation_cost_ledger",
    "evaluation_gate_results",
)

ARTIFACT_IDENTITIES = {
    "evaluation_policies": ("policy_sha256", "phase5-evaluation-policy-v1"),
    "evaluation_feature_specs": (
        "feature_spec_sha256",
        "phase5-feature-specification-v1",
    ),
    "evaluation_label_specs": (
        "label_spec_sha256",
        "phase5-label-specification-v1",
    ),
    "evaluation_blocked_outcomes": (
        "outcome_sha256",
        "phase5-evaluation-blocked-outcome-v1",
    ),
    "evaluation_reports": ("report_sha256", "phase5-evaluation-artifact-v1"),
    "evaluation_report_snapshots": (
        "report_snapshot_sha256",
        "phase5-report-snapshot-v1",
    ),
    "evaluation_trials": ("trial_sha256", "phase5-trial-v1"),
    "evaluation_folds": ("fold_sha256", "phase5-fold-v1"),
    "evaluation_preprocessing_fits": (
        "statistics_sha256",
        "phase5-preprocessing-fit-v1",
    ),
    "evaluation_oos_ledger": ("oos_entry_sha256", "phase5-ledger-entry-v1"),
    "evaluation_cost_ledger": ("cost_entry_sha256", "phase5-cost-entry-v1"),
    "evaluation_gate_results": (
        "gate_result_sha256",
        "phase5-gate-result-v1",
    ),
}


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _artifact_payload_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        _created_at(),
    ]


def upgrade() -> None:
    op.create_table(
        "evaluation_policies",
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("strategy_family", sa.String(length=64), nullable=False),
        sa.Column("selection_scope", sa.String(length=256), nullable=False),
        sa.Column("approved_by", sa.String(length=256), nullable=False),
        sa.Column("synthetic_fixture_policy", sa.Boolean(), nullable=False),
        sa.Column(
            "signal_specification",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "forecast_horizon",
            sa.String(length=256),
            nullable=False,
        ),
        sa.Column(
            "required_snapshot_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "label_interval_rule",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column(
            "transaction_cost_model",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "slippage_model",
            sa.String(length=256),
            nullable=False,
        ),
        sa.Column(
            "walk_forward_geometry",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "risk_limits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "selection_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "sample_adequacy_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("missing_return_policy", sa.String(length=128), nullable=False),
        sa.Column("no_trade_return_policy", sa.String(length=128), nullable=False),
        sa.Column(
            "regime_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "reproducibility_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "cost_stress_multiplier",
            sa.Numeric(precision=20, scale=8),
            nullable=False,
        ),
        sa.Column("expected_feature_spec_count", sa.Integer(), nullable=False),
        sa.Column("expected_label_spec_count", sa.Integer(), nullable=False),
        sa.Column(
            "feature_spec_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "label_spec_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "policy_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_policy_sha256",
        ),
        sa.CheckConstraint(
            "policy_version >= 1 "
            "AND schema_version = 'phase5-evaluation-policy-v1' "
            "AND strategy_family IN ("
            "'A_CROSS_SECTIONAL_EQUITY_RANKING',"
            "'B_TIME_SERIES_MOMENTUM_REGIME',"
            "'C_OFFICIAL_EVENT_TEXT_OVERLAY') "
            "AND btrim(selection_scope) <> '' AND btrim(approved_by) <> '' "
            "AND synthetic_fixture_policy AND btrim(forecast_horizon) <> '' "
            "AND btrim(label_interval_rule) <> '' AND btrim(slippage_model) <> ''",
            name="ck_eval_policy_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(signal_specification) = 'object' "
            "AND jsonb_typeof(required_snapshot_capabilities) = 'array' "
            "AND jsonb_array_length(required_snapshot_capabilities) >= 1 "
            "AND jsonb_typeof(transaction_cost_model) = 'object' "
            "AND jsonb_typeof(walk_forward_geometry) = 'object' "
            "AND jsonb_typeof(risk_limits) = 'object' "
            "AND jsonb_typeof(selection_policy) = 'object' "
            "AND jsonb_typeof(sample_adequacy_policy) = 'object' "
            "AND jsonb_typeof(regime_policy) = 'object' "
            "AND jsonb_typeof(reproducibility_policy) = 'object' "
            "AND jsonb_typeof(feature_spec_hashes) = 'array' "
            "AND jsonb_typeof(label_spec_hashes) = 'array' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_policy_json_shapes",
        ),
        sa.CheckConstraint(
            "expected_feature_spec_count >= 1 "
            "AND expected_label_spec_count >= 1 "
            "AND cost_stress_multiplier >= 2",
            name="ck_eval_policy_required_counts",
        ),
        sa.CheckConstraint(
            "missing_return_policy = 'block_missing_return_v1' "
            "AND no_trade_return_policy = 'explicit_zero_research_observation_v1'",
            name="ck_eval_policy_return_handling",
        ),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "policy_version",
            name="pk_evaluation_policies",
        ),
        sa.UniqueConstraint("policy_sha256", name="uq_eval_policy_sha256"),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            "policy_sha256",
            name="uq_eval_policy_version_sha256",
        ),
    )

    op.create_table(
        "evaluation_feature_specs",
        sa.Column("feature_spec_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_spec_sha256", sa.String(length=64), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("feature_name", sa.String(length=256), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=64), nullable=False),
        sa.Column(
            "information_interval",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "required_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "feature_spec_sha256 ~ '^[0-9a-f]{64}$' AND policy_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_feature_spec_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(feature_name) <> '' "
            "AND feature_schema_version = 'phase5-feature-specification-v1'",
            name="ck_eval_feature_spec_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(information_interval) = 'object' "
            "AND jsonb_typeof(required_capabilities) = 'array' "
            "AND jsonb_array_length(required_capabilities) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_feature_spec_json",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "policy_version", "policy_sha256"],
            [
                "evaluation_policies.policy_id",
                "evaluation_policies.policy_version",
                "evaluation_policies.policy_sha256",
            ],
            name="fk_eval_feature_spec_policy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "policy_version",
            "feature_spec_id",
            name="pk_evaluation_feature_specs",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            "feature_spec_sha256",
            name="uq_eval_feature_spec_sha256",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            "ordinal",
            name="uq_eval_feature_spec_policy_ordinal",
        ),
    )

    op.create_table(
        "evaluation_label_specs",
        sa.Column("label_spec_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label_spec_sha256", sa.String(length=64), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("label_name", sa.String(length=256), nullable=False),
        sa.Column("label_schema_version", sa.String(length=64), nullable=False),
        sa.Column(
            "information_interval",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "forecast_horizon",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "label_spec_sha256 ~ '^[0-9a-f]{64}$' AND policy_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_label_spec_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(label_name) <> '' "
            "AND label_schema_version = 'phase5-label-specification-v1'",
            name="ck_eval_label_spec_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(information_interval) = 'object' "
            "AND jsonb_typeof(forecast_horizon) = 'object' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_label_spec_json",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "policy_version", "policy_sha256"],
            [
                "evaluation_policies.policy_id",
                "evaluation_policies.policy_version",
                "evaluation_policies.policy_sha256",
            ],
            name="fk_eval_label_spec_policy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "policy_version",
            "label_spec_id",
            name="pk_evaluation_label_specs",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            "label_spec_sha256",
            name="uq_eval_label_spec_sha256",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            "ordinal",
            name="uq_eval_label_spec_policy_ordinal",
        ),
    )

    op.create_table(
        "evaluation_blocked_outcomes",
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "idempotency_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("submission_sha256", sa.String(length=64), nullable=False),
        sa.Column("submission_canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "submission_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "snapshot_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("fixture_id", sa.String(length=256), nullable=False),
        sa.Column("resolved_policy_sha256", sa.String(length=64), nullable=True),
        sa.Column("resolved_fixture_sha256", sa.String(length=64), nullable=True),
        sa.Column("resolved_fixture_random_seed", sa.BigInteger(), nullable=True),
        sa.Column("resolved_raw_trial_count", sa.BigInteger(), nullable=True),
        sa.Column(
            "resolved_snapshots",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("failure_stage", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claim", sa.Boolean(), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "outcome_sha256 ~ '^[0-9a-f]{64}$' "
            "AND idempotency_sha256 ~ '^[0-9a-f]{64}$' "
            "AND submission_sha256 ~ '^[0-9a-f]{64}$' "
            "AND (resolved_policy_sha256 IS NULL "
            "OR resolved_policy_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (resolved_fixture_sha256 IS NULL "
            "OR resolved_fixture_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (git_sha IS NULL OR git_sha ~ '^[0-9a-f]{40}$')",
            name="ck_eval_blocked_outcome_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase5-blocked-evaluation-outcome-v1' "
            "AND policy_version >= 1 AND btrim(fixture_id) <> '' "
            "AND failure_stage IN ('precheck','policy_resolution','fixture_resolution',"
            "'snapshot_resolution','snapshot_lineage','engine_computation') "
            "AND state IN ('BLOCKED_MISSING_POLICY','BLOCKED_UNCOMPUTABLE') "
            "AND ((resolved_fixture_sha256 IS NULL "
            "AND resolved_fixture_random_seed IS NULL "
            "AND resolved_raw_trial_count IS NULL) OR "
            "(resolved_fixture_sha256 IS NOT NULL "
            "AND resolved_fixture_random_seed >= 0 "
            "AND resolved_raw_trial_count >= 1)) "
            "AND synthetic AND no_real_performance_claim",
            name="ck_eval_blocked_outcome_identity",
        ),
        sa.CheckConstraint(
            "btrim(idempotency_canonical_json) <> '' "
            "AND idempotency_canonical_json::jsonb = idempotency_payload "
            "AND jsonb_typeof(idempotency_payload) = 'object' "
            "AND btrim(submission_canonical_json) <> '' "
            "AND submission_canonical_json::jsonb = submission_payload "
            "AND jsonb_typeof(submission_payload) = 'object' "
            "AND jsonb_typeof(snapshot_ids) = 'array' "
            "AND jsonb_array_length(snapshot_ids) >= 1 "
            "AND jsonb_typeof(resolved_snapshots) = 'array' "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_blocked_outcome_json",
        ),
        sa.PrimaryKeyConstraint("outcome_id", name="pk_evaluation_blocked_outcomes"),
        sa.UniqueConstraint(
            "outcome_sha256",
            name="uq_eval_blocked_outcome_sha256",
        ),
        sa.UniqueConstraint(
            "idempotency_sha256",
            name="uq_eval_blocked_outcome_idempotency_sha256",
        ),
    )
    op.create_index(
        "ix_eval_blocked_outcomes_created",
        "evaluation_blocked_outcomes",
        ["created_at_utc", "outcome_id"],
    )

    op.create_table(
        "evaluation_reports",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_schema_version", sa.String(length=64), nullable=False),
        sa.Column("run_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("run_fingerprint_canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "run_fingerprint_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column("mapping_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("fixture_id", sa.String(length=256), nullable=False),
        sa.Column("fixture_sha256", sa.String(length=64), nullable=False),
        sa.Column("snapshot_bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("snapshot_bundle_canonical_json", sa.Text(), nullable=False),
        sa.Column("sample_lineage_sha256", sa.String(length=64), nullable=False),
        sa.Column("sample_lineage_canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "source_observations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "sample_lineage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("git_sha", sa.String(length=40), nullable=False),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_trial_count", sa.Integer(), nullable=False),
        sa.Column(
            "effective_trial_count",
            sa.Numeric(precision=38, scale=24),
            nullable=False,
        ),
        sa.Column("effective_trial_count_method", sa.String(length=128), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claim", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("expected_snapshot_count", sa.Integer(), nullable=False),
        sa.Column("expected_source_observation_count", sa.Integer(), nullable=False),
        sa.Column("expected_sample_lineage_count", sa.Integer(), nullable=False),
        sa.Column("expected_trial_count", sa.Integer(), nullable=False),
        sa.Column("expected_fold_count", sa.Integer(), nullable=False),
        sa.Column("expected_preprocessing_fit_count", sa.Integer(), nullable=False),
        sa.Column("expected_oos_ledger_count", sa.Integer(), nullable=False),
        sa.Column("expected_cost_ledger_count", sa.Integer(), nullable=False),
        sa.Column("expected_gate_result_count", sa.Integer(), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND run_fingerprint_sha256 ~ '^[0-9a-f]{64}$' "
            "AND policy_sha256 ~ '^[0-9a-f]{64}$' "
            "AND mapping_input_sha256 ~ '^[0-9a-f]{64}$' "
            "AND configuration_sha256 ~ '^[0-9a-f]{64}$' "
            "AND fixture_sha256 ~ '^[0-9a-f]{64}$' "
            "AND snapshot_bundle_sha256 ~ '^[0-9a-f]{64}$' "
            "AND sample_lineage_sha256 ~ '^[0-9a-f]{64}$' "
            "AND git_sha ~ '^[0-9a-f]{40}$'",
            name="ck_eval_report_hashes",
        ),
        sa.CheckConstraint(
            "report_schema_version = 'phase5-evaluation-report-v1' "
            "AND btrim(fixture_id) <> '' "
            "AND btrim(effective_trial_count_method) <> '' "
            "AND policy_version >= 1 AND mapping_version >= 1 "
            "AND random_seed >= 0",
            name="ck_eval_report_identity",
        ),
        sa.CheckConstraint(
            "raw_trial_count >= 1 "
            "AND effective_trial_count > 1 "
            "AND effective_trial_count <= raw_trial_count "
            "AND expected_snapshot_count >= 1 "
            "AND expected_source_observation_count >= 1 "
            "AND expected_sample_lineage_count >= 4 "
            "AND expected_trial_count = raw_trial_count "
            "AND expected_fold_count >= 1 "
            "AND expected_preprocessing_fit_count >= 1 "
            "AND expected_oos_ledger_count >= 1 "
            "AND expected_cost_ledger_count >= 3 "
            "AND expected_cost_ledger_count % 3 = 0 "
            "AND expected_gate_result_count = 12",
            name="ck_eval_report_counts",
        ),
        sa.CheckConstraint(
            "synthetic AND no_real_performance_claim",
            name="ck_eval_report_synthetic_only",
        ),
        sa.CheckConstraint(
            "state IN ("
            "'PASS_RESEARCH','FAIL_REJECT','BLOCKED_MISSING_POLICY',"
            "'BLOCKED_UNCOMPUTABLE','RESEARCH_ONLY_REGIME_DEPENDENT')",
            name="ck_eval_report_state",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(run_fingerprint_payload) = 'object' "
            "AND jsonb_typeof(source_observations) = 'array' "
            "AND jsonb_typeof(sample_lineage) = 'array' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_report_json",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "policy_version", "policy_sha256"],
            [
                "evaluation_policies.policy_id",
                "evaluation_policies.policy_version",
                "evaluation_policies.policy_sha256",
            ],
            name="fk_eval_report_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["research_mapping_versions.id"],
            name="fk_eval_report_mapping",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("report_id", name="pk_evaluation_reports"),
        sa.UniqueConstraint("report_sha256", name="uq_eval_report_sha256"),
        sa.UniqueConstraint(
            "run_fingerprint_sha256",
            name="uq_eval_report_run_fingerprint",
        ),
        sa.UniqueConstraint(
            "report_id",
            "report_sha256",
            name="uq_eval_report_id_sha256",
        ),
    )
    op.create_index(
        "ix_eval_reports_mapping_created",
        "evaluation_reports",
        ["mapping_id", "created_at_utc", "report_id"],
    )
    op.create_index(
        "ix_eval_reports_policy_created",
        "evaluation_reports",
        ["policy_id", "created_at_utc", "report_id"],
    )

    op.create_table(
        "evaluation_report_snapshots",
        sa.Column("report_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("as_of_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_version", sa.String(length=256), nullable=False),
        sa.Column("dataset_id", sa.String(length=256), nullable=False),
        sa.Column("product_id", sa.String(length=256), nullable=False),
        sa.Column("dataset_schema_id", sa.String(length=256), nullable=False),
        sa.Column("dataset_schema_version", sa.String(length=256), nullable=False),
        sa.Column(
            "dataset_schema_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("quality_status", sa.String(length=64), nullable=False),
        sa.Column("fixture_set_version", sa.String(length=64), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "report_snapshot_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND snapshot_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_report_snapshot_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(capability) <> '' "
            "AND btrim(provider_id) <> '' AND btrim(adapter_id) <> '' "
            "AND btrim(adapter_version) <> '' AND btrim(dataset_id) <> '' "
            "AND btrim(product_id) <> '' AND btrim(dataset_schema_id) <> '' "
            "AND btrim(dataset_schema_version) <> '' "
            "AND jsonb_typeof(dataset_schema_versions) = 'array' "
            "AND jsonb_array_length(dataset_schema_versions) >= 1 "
            "AND quality_status IN ("
            "'data_quality_accepted','data_quality_accepted_with_warnings') "
            "AND btrim(fixture_set_version) <> '' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_report_snapshot_identity",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_report_snapshot_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_eval_report_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_sha256"],
            ["data_snapshots.snapshot_sha256"],
            name="fk_eval_report_snapshot_sha",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_snapshot_id",
            name="pk_evaluation_report_snapshots",
        ),
        sa.UniqueConstraint(
            "report_snapshot_sha256",
            name="uq_eval_report_snapshot_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_report_snapshot_ordinal",
        ),
        sa.UniqueConstraint(
            "report_id",
            "snapshot_id",
            name="uq_eval_report_snapshot_id",
        ),
        sa.UniqueConstraint(
            "report_id",
            "capability",
            name="uq_eval_report_snapshot_capability",
        ),
    )

    op.create_table(
        "evaluation_trials",
        sa.Column("trial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trial_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("trial_key", sa.String(length=256), nullable=False),
        sa.Column("strategy_family", sa.String(length=64), nullable=False),
        sa.Column("selection_scope", sa.String(length=256), nullable=False),
        sa.Column("initiated_by", sa.String(length=256), nullable=False),
        sa.Column("initiated_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("oos_return_state", sa.String(length=64), nullable=False),
        sa.Column(
            "net_returns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "return_statuses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "return_timestamps_utc",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("return_observation_count", sa.Integer(), nullable=False),
        sa.Column("missing_return_count", sa.Integer(), nullable=False),
        sa.Column("no_trade_count", sa.Integer(), nullable=False),
        sa.Column("config_sha256", sa.String(length=64), nullable=False),
        sa.Column("config_canonical_json", sa.Text(), nullable=False),
        sa.Column(
            "config_preimage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "trial_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND config_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_trial_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(trial_key) <> '' "
            "AND btrim(strategy_family) <> '' AND btrim(selection_scope) <> '' "
            "AND btrim(initiated_by) <> '' "
            "AND status IN ('completed','failed','abandoned','no_return') "
            "AND btrim(config_canonical_json) <> '' "
            "AND config_canonical_json::jsonb = config_preimage "
            "AND jsonb_typeof(config_preimage) = 'object' "
            "AND jsonb_typeof(configuration) = 'object' "
            "AND jsonb_typeof(net_returns) = 'array' "
            "AND jsonb_typeof(return_statuses) = 'array' "
            "AND jsonb_typeof(return_timestamps_utc) = 'array' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_trial_status",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND failure_reason IS NULL) OR "
            "(status IN ('failed','abandoned') AND failure_reason IS NOT NULL "
            "AND btrim(failure_reason) <> '') OR "
            "(status = 'no_return' AND failure_reason IS NOT NULL "
            "AND btrim(failure_reason) <> '')",
            name="ck_eval_trial_failure_detail",
        ),
        sa.CheckConstraint(
            "return_observation_count >= 0 "
            "AND missing_return_count >= 0 "
            "AND no_trade_count >= 0 "
            "AND return_observation_count = jsonb_array_length(net_returns) "
            "AND return_observation_count = jsonb_array_length(return_statuses) "
            "AND return_observation_count = jsonb_array_length(return_timestamps_utc) "
            "AND missing_return_count <= return_observation_count "
            "AND no_trade_count <= return_observation_count "
            "AND return_statuses <@ "
            '\'["observed","no_trade","delisted","missing"]\'::jsonb '
            "AND ((status = 'completed' "
            "AND oos_return_state = 'complete_common_calendar' "
            "AND return_observation_count >= 2 AND missing_return_count = 0) OR "
            "(status IN ('failed','abandoned') "
            "AND oos_return_state = status AND return_observation_count = 0 "
            "AND missing_return_count = 0 AND no_trade_count = 0) OR "
            "(status = 'no_return' AND oos_return_state = 'no_return' "
            "AND return_observation_count >= 2 "
            "AND missing_return_count = return_observation_count "
            "AND no_trade_count = 0))",
            name="ck_eval_trial_return_calendar",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_trial_report",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_id",
            "trial_id",
            name="pk_evaluation_trials",
        ),
        sa.UniqueConstraint(
            "report_id",
            "trial_sha256",
            name="uq_eval_trial_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_trial_report_ordinal",
        ),
    )

    op.create_table(
        "evaluation_folds",
        sa.Column("fold_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fold_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("fold_kind", sa.String(length=16), nullable=False),
        sa.Column("parent_fold_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("train_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_row_count", sa.Integer(), nullable=False),
        sa.Column("test_row_count", sa.Integer(), nullable=False),
        sa.Column("purged_row_count", sa.Integer(), nullable=False),
        sa.Column("embargoed_row_count", sa.Integer(), nullable=False),
        sa.Column("embargo_duration_seconds", sa.BigInteger(), nullable=False),
        sa.Column("embargo_applied", sa.Boolean(), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "fold_sha256 ~ '^[0-9a-f]{64}$' AND report_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_fold_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND fold_kind IN ('outer','inner','cpcv') "
            "AND ((fold_kind IN ('outer','cpcv') AND parent_fold_id IS NULL) OR "
            "(fold_kind = 'inner' AND parent_fold_id IS NOT NULL))",
            name="ck_eval_fold_level",
        ),
        sa.CheckConstraint(
            "train_start_utc <= train_end_utc "
            "AND test_start_utc <= test_end_utc "
            "AND (fold_kind = 'cpcv' OR train_end_utc < test_start_utc)",
            name="ck_eval_fold_chronology",
        ),
        sa.CheckConstraint(
            "training_row_count >= 1 AND test_row_count >= 1 "
            "AND purged_row_count >= 0 AND embargoed_row_count >= 0 "
            "AND embargo_duration_seconds >= 0 "
            "AND ((NOT embargo_applied AND embargoed_row_count = 0 "
            "AND embargo_duration_seconds = 0) OR "
            "(embargo_applied AND embargo_duration_seconds > 0)) "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_fold_counts_embargo",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_fold_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "parent_fold_id"],
            ["evaluation_folds.report_id", "evaluation_folds.fold_id"],
            name="fk_eval_fold_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_id",
            "fold_id",
            name="pk_evaluation_folds",
        ),
        sa.UniqueConstraint(
            "report_id",
            "fold_sha256",
            name="uq_eval_fold_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_fold_report_ordinal",
        ),
    )

    op.create_table(
        "evaluation_preprocessing_fits",
        sa.Column("fit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fit_sha256", sa.String(length=64), nullable=False),
        sa.Column("statistics_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("fold_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("transformer_id", sa.String(length=256), nullable=False),
        sa.Column("transformer_version", sa.String(length=128), nullable=False),
        sa.Column("training_row_count", sa.Integer(), nullable=False),
        sa.Column(
            "train_sample_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("train_sample_ids_sha256", sa.String(length=64), nullable=False),
        sa.Column("mean", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("standard_deviation", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("ddof", sa.Integer(), nullable=False),
        sa.Column(
            "record_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "fit_sha256 ~ '^[0-9a-f]{64}$' "
            "AND statistics_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND train_sample_ids_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_preprocessing_fit_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND training_row_count >= 2 "
            "AND btrim(transformer_id) <> '' "
            "AND btrim(transformer_version) <> '' "
            "AND transformer_version = 'phase5-train-only-standardizer-v1' "
            "AND jsonb_typeof(train_sample_ids) = 'array' "
            "AND jsonb_array_length(train_sample_ids) = training_row_count "
            "AND standard_deviation > 0 AND ddof = 1 "
            "AND jsonb_typeof(record_payload) = 'object' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_preprocessing_fit_identity",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_preprocessing_fit_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "fold_id"],
            ["evaluation_folds.report_id", "evaluation_folds.fold_id"],
            name="fk_eval_preprocessing_fit_fold",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_id",
            "fit_id",
            name="pk_evaluation_preprocessing_fits",
        ),
        sa.UniqueConstraint(
            "report_id",
            "statistics_sha256",
            name="uq_eval_preprocessing_statistics_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_preprocessing_fit_ordinal",
        ),
        sa.UniqueConstraint(
            "report_id",
            "fold_id",
            name="uq_eval_preprocessing_fit_fold",
        ),
    )

    op.create_table(
        "evaluation_oos_ledger",
        sa.Column("oos_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("oos_entry_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("trial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fold_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.String(length=256), nullable=False),
        sa.Column("sample_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "source_observation_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("information_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("information_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("label_t0_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("label_t1_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prediction_value", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("gross_return", sa.Numeric(precision=38, scale=30), nullable=True),
        sa.Column("baseline_net_return", sa.Numeric(precision=38, scale=30), nullable=True),
        sa.Column("return_status", sa.String(length=32), nullable=False),
        sa.Column("delisting_return_handled", sa.Boolean(), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "oos_entry_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND sample_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_oos_entry_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(sample_id) <> '' "
            "AND information_start_utc <= information_end_utc "
            "AND information_end_utc <= decision_time_utc "
            "AND decision_time_utc <= label_t0_utc "
            "AND label_t0_utc < label_t1_utc "
            "AND jsonb_typeof(source_observation_refs) = 'array' "
            "AND jsonb_array_length(source_observation_refs) >= 1",
            name="ck_eval_oos_information_intervals",
        ),
        sa.CheckConstraint(
            "return_status IN ('observed','no_trade','delisted','missing') "
            "AND ((return_status = 'missing' "
            "AND gross_return IS NULL AND baseline_net_return IS NULL) OR "
            "(return_status = 'no_trade' "
            "AND gross_return = 0 AND baseline_net_return = 0) OR "
            "(return_status IN ('observed','delisted') "
            "AND gross_return IS NOT NULL AND baseline_net_return IS NOT NULL)) "
            "AND (return_status <> 'delisted' OR delisting_return_handled) "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_oos_return_handling",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_oos_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "trial_id"],
            ["evaluation_trials.report_id", "evaluation_trials.trial_id"],
            name="fk_eval_oos_trial",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "fold_id"],
            ["evaluation_folds.report_id", "evaluation_folds.fold_id"],
            name="fk_eval_oos_fold",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_id",
            "oos_entry_id",
            name="pk_evaluation_oos_ledger",
        ),
        sa.UniqueConstraint(
            "report_id",
            "oos_entry_sha256",
            name="uq_eval_oos_entry_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_oos_report_ordinal",
        ),
    )

    op.create_table(
        "evaluation_cost_ledger",
        sa.Column("cost_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_entry_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.String(length=256), nullable=False),
        sa.Column("scenario", sa.String(length=32), nullable=False),
        sa.Column("allocation_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("return_status", sa.String(length=32), nullable=False),
        sa.Column("stress_multiplier", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("rejected_quantity", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("unfilled_quantity", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("fill_status", sa.String(length=32), nullable=False),
        sa.Column("hard_to_borrow_available", sa.Boolean(), nullable=False),
        sa.Column("gross_return", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("fee_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("spread_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("impact_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("latency_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("borrow_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("capacity_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("net_return", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("participation_rate", sa.Numeric(precision=38, scale=30), nullable=False),
        sa.Column("capacity_breached", sa.Boolean(), nullable=False),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "cost_entry_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND allocation_input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_eval_cost_entry_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND btrim(sample_id) <> '' "
            "AND scenario IN ('baseline','all_cost_stress','liquidity_stress') "
            "AND return_status IN ('observed','no_trade','delisted') "
            "AND requested_quantity >= 0 AND filled_quantity >= 0 "
            "AND rejected_quantity >= 0 AND unfilled_quantity >= 0 "
            "AND filled_quantity + unfilled_quantity = requested_quantity "
            "AND rejected_quantity = unfilled_quantity "
            "AND ((return_status = 'no_trade' AND fill_status = 'no_trade' "
            "AND requested_quantity = 0 AND filled_quantity = 0 "
            "AND rejected_quantity = 0 AND unfilled_quantity = 0) OR "
            "(return_status IN ('observed','delisted') AND requested_quantity > 0 "
            "AND ((fill_status = 'filled' AND unfilled_quantity = 0) OR "
            "(fill_status = 'capacity_rejected' AND filled_quantity = 0 "
            "AND unfilled_quantity = requested_quantity))))",
            name="ck_eval_cost_scenario",
        ),
        sa.CheckConstraint(
            "fee_cost >= 0 AND spread_cost >= 0 AND impact_cost >= 0 "
            "AND latency_cost >= 0 AND borrow_cost >= 0 AND capacity_cost >= 0 "
            "AND abs(total_cost - (fee_cost + spread_cost + impact_cost + latency_cost "
            "+ borrow_cost + capacity_cost)) <= power(10::numeric, -29) "
            "AND abs(net_return - (gross_return - total_cost)) <= power(10::numeric, -29) "
            "AND participation_rate >= 0 "
            "AND capacity_breached = (fill_status = 'capacity_rejected') "
            "AND (fill_status = 'filled' OR (gross_return = 0 AND fee_cost = 0 "
            "AND spread_cost = 0 AND impact_cost = 0 AND latency_cost = 0 "
            "AND borrow_cost = 0 AND capacity_cost = 0 AND total_cost = 0 "
            "AND net_return = 0 AND participation_rate = 0))",
            name="ck_eval_cost_components",
        ),
        sa.CheckConstraint(
            "(scenario = 'baseline' AND stress_multiplier = 1) OR "
            "(scenario = 'all_cost_stress' AND stress_multiplier >= 2) OR "
            "(scenario = 'liquidity_stress' AND stress_multiplier > 1)",
            name="ck_eval_cost_stress_multiplier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_eval_cost_payload",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_cost_report",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "report_id",
            "cost_entry_id",
            name="pk_evaluation_cost_ledger",
        ),
        sa.UniqueConstraint(
            "report_id",
            "cost_entry_sha256",
            name="uq_eval_cost_entry_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_cost_report_ordinal",
        ),
        sa.UniqueConstraint(
            "report_id",
            "sample_id",
            "scenario",
            name="uq_eval_cost_report_key_scenario",
        ),
    )

    op.create_table(
        "evaluation_gate_results",
        sa.Column("gate_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gate_result_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("gate_code", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("computable", sa.Boolean(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("metric_value", sa.Numeric(precision=38, scale=30), nullable=True),
        sa.Column("threshold_value", sa.Numeric(precision=38, scale=30), nullable=True),
        *_artifact_payload_columns(),
        sa.CheckConstraint(
            "gate_result_sha256 ~ '^[0-9a-f]{64}$' "
            "AND report_sha256 ~ '^[0-9a-f]{64}$' "
            "AND config_hash ~ '^[0-9a-f]{64}$'",
            name="ck_eval_gate_result_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND gate_code IN ("
            "'DATA_PIT','CV_CHRONOLOGY','PREPROCESSING','TRIAL_REGISTRY',"
            "'DSR','PBO','COST_STRESS','LEAKAGE','SAMPLE_ADEQUACY','REGIME',"
            "'RISK_LIMITS','REPRODUCIBILITY')",
            name="ck_eval_gate_code",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'pass','fail','blocked_missing_policy','blocked_uncomputable','research_only') "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND ((outcome = 'pass' AND computable AND passed AND NOT blocking) OR "
            "(outcome = 'fail' AND computable AND NOT passed AND blocking) OR "
            "(outcome IN ('blocked_missing_policy','blocked_uncomputable') "
            "AND NOT computable AND NOT passed AND blocking) OR "
            "(outcome = 'research_only' AND computable AND NOT passed AND NOT blocking)) "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_eval_gate_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "report_sha256"],
            ["evaluation_reports.report_id", "evaluation_reports.report_sha256"],
            name="fk_eval_gate_report",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "gate_result_id",
            name="pk_evaluation_gate_results",
        ),
        sa.UniqueConstraint(
            "gate_result_sha256",
            name="uq_eval_gate_result_sha256",
        ),
        sa.UniqueConstraint(
            "report_id",
            "ordinal",
            name="uq_eval_gate_report_ordinal",
        ),
        sa.UniqueConstraint(
            "report_id",
            "gate_code",
            name="uq_eval_gate_report_code",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_artifact_identity()
        RETURNS trigger AS $$
        DECLARE
            row_value jsonb;
            artifact_hash text;
            artifact_canonical_json text;
            artifact_payload jsonb;
            expected_hash text;
        BEGIN
            row_value := to_jsonb(NEW);
            artifact_hash := row_value->>TG_ARGV[0];
            artifact_canonical_json := row_value->>'canonical_json';
            artifact_payload := row_value->'payload';

            IF artifact_canonical_json IS NULL OR btrim(artifact_canonical_json) = ''
               OR artifact_canonical_json::jsonb IS DISTINCT FROM artifact_payload THEN
                RAISE EXCEPTION 'Phase 5 artifact canonical payload mismatch';
            END IF;

            expected_hash := encode(
                sha256(
                    convert_to(TG_ARGV[1], 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(artifact_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF artifact_hash IS DISTINCT FROM expected_hash THEN
                RAISE EXCEPTION 'Phase 5 artifact hash mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    for table, (hash_column, domain) in ARTIFACT_IDENTITIES.items():
        op.execute(
            f"""
            CREATE TRIGGER {table}_05_identity
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase5_artifact_identity(
                '{hash_column}', '{domain}'
            )
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_blocked_outcome()
        RETURNS trigger AS $$
        DECLARE
            expected_submission_hash text;
            expected_idempotency_hash text;
        BEGIN
            IF NEW.submission_canonical_json::jsonb
                    IS DISTINCT FROM NEW.submission_payload THEN
                RAISE EXCEPTION 'Phase 5 blocked submission canonical payload mismatch';
            END IF;
            expected_submission_hash := encode(
                sha256(
                    convert_to('phase5-evaluation-blocked-submission-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(NEW.submission_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF NEW.submission_sha256 IS DISTINCT FROM expected_submission_hash THEN
                RAISE EXCEPTION 'Phase 5 blocked submission hash mismatch';
            END IF;

            IF NEW.idempotency_canonical_json::jsonb
                    IS DISTINCT FROM NEW.idempotency_payload THEN
                RAISE EXCEPTION 'Phase 5 blocked idempotency canonical payload mismatch';
            END IF;
            expected_idempotency_hash := encode(
                sha256(
                    convert_to(
                        'phase5-evaluation-blocked-outcome-idempotency-v1',
                        'UTF8'
                    )
                    || decode('00', 'hex')
                    || convert_to(NEW.idempotency_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF NEW.idempotency_sha256 IS DISTINCT FROM expected_idempotency_hash THEN
                RAISE EXCEPTION 'Phase 5 blocked idempotency hash mismatch';
            END IF;

            IF NEW.payload - 'idempotency_sha256' - 'created_at_utc'
                    IS DISTINCT FROM NEW.idempotency_payload
               OR NEW.payload->>'idempotency_sha256'
                    IS DISTINCT FROM NEW.idempotency_sha256
               OR (NEW.payload->>'created_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.created_at_utc THEN
                RAISE EXCEPTION 'Phase 5 blocked outcome full payload mismatch';
            END IF;

            IF NEW.submission_payload->>'policy_id' IS DISTINCT FROM NEW.policy_id::text
               OR (NEW.submission_payload->>'policy_version')::integer
                    IS DISTINCT FROM NEW.policy_version
               OR NEW.submission_payload->>'mapping_id' IS DISTINCT FROM NEW.mapping_id::text
               OR NEW.submission_payload->'snapshot_ids' IS DISTINCT FROM NEW.snapshot_ids
               OR NEW.submission_payload->>'fixture_id' IS DISTINCT FROM NEW.fixture_id THEN
                RAISE EXCEPTION 'Phase 5 blocked submission columns differ from payload';
            END IF;

            IF NEW.payload->>'artifact_type'
                    IS DISTINCT FROM 'blocked_synthetic_research_evaluation'
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR NEW.payload->>'submission_sha256' IS DISTINCT FROM NEW.submission_sha256
               OR NEW.payload->'request' IS DISTINCT FROM NEW.submission_payload
               OR NEW.payload->>'resolved_policy_sha256'
                    IS DISTINCT FROM NEW.resolved_policy_sha256
               OR NEW.payload->>'resolved_fixture_sha256'
                    IS DISTINCT FROM NEW.resolved_fixture_sha256
               OR (NEW.payload->>'resolved_fixture_random_seed')::bigint
                    IS DISTINCT FROM NEW.resolved_fixture_random_seed
               OR (NEW.payload->>'resolved_raw_trial_count')::bigint
                    IS DISTINCT FROM NEW.resolved_raw_trial_count
               OR NEW.payload->'resolved_snapshots' IS DISTINCT FROM NEW.resolved_snapshots
               OR NEW.payload->>'code_version_git_sha' IS DISTINCT FROM NEW.git_sha
               OR NEW.payload->>'failure_stage' IS DISTINCT FROM NEW.failure_stage
               OR NEW.payload->>'status' IS DISTINCT FROM 'blocked'
               OR NEW.payload->>'promotion_state' IS DISTINCT FROM NEW.state
               OR NEW.payload->'reason_codes' IS DISTINCT FROM NEW.reason_codes
               OR (NEW.payload->>'synthetic')::boolean IS DISTINCT FROM NEW.synthetic
               OR (NEW.payload->>'no_real_performance_claimed')::boolean
                    IS DISTINCT FROM NEW.no_real_performance_claim THEN
                RAISE EXCEPTION 'Phase 5 blocked outcome columns differ from hash preimage';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_blocked_outcomes_10_payload
        BEFORE INSERT ON evaluation_blocked_outcomes
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_blocked_outcome()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_policy_definition()
        RETURNS trigger AS $$
        DECLARE
            sorted_capabilities jsonb;
        BEGIN
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO sorted_capabilities
            FROM jsonb_array_elements_text(NEW.required_snapshot_capabilities) AS item(value);

            IF NEW.required_snapshot_capabilities IS DISTINCT FROM sorted_capabilities
               OR jsonb_array_length(NEW.required_snapshot_capabilities)
                    <> (SELECT count(DISTINCT value)
                        FROM jsonb_array_elements_text(
                            NEW.required_snapshot_capabilities
                        ) AS item(value)) THEN
                RAISE EXCEPTION 'Phase 5 required capabilities must be unique and sorted';
            END IF;

            IF NEW.payload->>'policy_id' IS DISTINCT FROM NEW.policy_id::text
               OR (NEW.payload->>'policy_version')::integer
                    IS DISTINCT FROM NEW.policy_version
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR NEW.payload->>'strategy_family' IS DISTINCT FROM NEW.strategy_family
               OR NEW.payload->>'selection_scope' IS DISTINCT FROM NEW.selection_scope
               OR NEW.payload->>'approved_by' IS DISTINCT FROM NEW.approved_by
               OR (NEW.payload->>'synthetic_fixture_policy')::boolean
                    IS DISTINCT FROM NEW.synthetic_fixture_policy
               OR NEW.payload->'signal_specification'
                    IS DISTINCT FROM NEW.signal_specification
               OR NEW.payload#>>'{signal_specification,forecast_horizon}'
                    IS DISTINCT FROM NEW.forecast_horizon
               OR NEW.payload->'required_snapshot_capabilities'
                    IS DISTINCT FROM NEW.required_snapshot_capabilities
               OR NEW.payload#>>'{label_specification,information_interval_rule}'
                    IS DISTINCT FROM NEW.label_interval_rule
               OR NEW.payload->'costs'
                    IS DISTINCT FROM NEW.transaction_cost_model
               OR NEW.payload#>>'{costs,slippage_model_id}'
                    IS DISTINCT FROM NEW.slippage_model
               OR NEW.payload->'walk_forward'
                    IS DISTINCT FROM NEW.walk_forward_geometry
               OR NEW.payload->'risk' IS DISTINCT FROM NEW.risk_limits
               OR NEW.payload->'selection' IS DISTINCT FROM NEW.selection_policy
               OR NEW.payload->'sample_adequacy'
                    IS DISTINCT FROM NEW.sample_adequacy_policy
               OR NEW.payload#>>'{label_specification,missing_return_policy}'
                    IS DISTINCT FROM NEW.missing_return_policy
               OR NEW.payload#>>'{sample_adequacy,missing_return_policy}'
                    IS DISTINCT FROM NEW.missing_return_policy
               OR NEW.payload#>>'{label_specification,no_trade_return_policy}'
                    IS DISTINCT FROM NEW.no_trade_return_policy
               OR NEW.payload#>>'{sample_adequacy,no_trade_return_policy}'
                    IS DISTINCT FROM NEW.no_trade_return_policy
               OR NEW.payload->'regimes' IS DISTINCT FROM NEW.regime_policy
               OR NEW.payload->'audit'
                    IS DISTINCT FROM NEW.reproducibility_policy
               OR (NEW.payload#>>'{stress,all_cost_multiplier}')::numeric
                    IS DISTINCT FROM NEW.cost_stress_multiplier
               OR NEW.feature_spec_hashes IS DISTINCT FROM jsonb_build_array(
                    NEW.payload#>>'{feature_specification,content_sha256}'
               )
               OR NEW.label_spec_hashes IS DISTINCT FROM jsonb_build_array(
                    NEW.payload#>>'{label_specification,content_sha256}'
               )
               OR NEW.expected_feature_spec_count <> 1
               OR NEW.expected_label_spec_count <> 1 THEN
                RAISE EXCEPTION 'Phase 5 policy columns are not bound by its frozen payload';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_policies_10_definition
        BEFORE INSERT ON evaluation_policies
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_policy_definition()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_report_header()
        RETURNS trigger AS $$
        DECLARE
            expected_run_fingerprint text;
            expected_configuration_hash text;
            expected_sample_lineage_hash text;
        BEGIN
            IF btrim(NEW.run_fingerprint_canonical_json) = ''
               OR NEW.run_fingerprint_canonical_json::jsonb
                    IS DISTINCT FROM NEW.run_fingerprint_payload THEN
                RAISE EXCEPTION 'Phase 5 run fingerprint canonical payload mismatch';
            END IF;

            expected_run_fingerprint := encode(
                sha256(
                    convert_to('phase5-evaluation-request-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(NEW.run_fingerprint_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF NEW.run_fingerprint_sha256 IS DISTINCT FROM expected_run_fingerprint THEN
                RAISE EXCEPTION 'Phase 5 run fingerprint hash mismatch';
            END IF;
            expected_configuration_hash := encode(
                sha256(
                    convert_to('phase5-evaluation-config-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(NEW.run_fingerprint_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF NEW.configuration_sha256 IS DISTINCT FROM expected_configuration_hash THEN
                RAISE EXCEPTION 'Phase 5 configuration hash mismatch';
            END IF;

            IF btrim(NEW.sample_lineage_canonical_json) = ''
               OR NEW.sample_lineage_canonical_json::jsonb
                    IS DISTINCT FROM NEW.sample_lineage THEN
                RAISE EXCEPTION 'Phase 5 sample lineage canonical payload mismatch';
            END IF;
            expected_sample_lineage_hash := encode(
                sha256(
                    convert_to('phase5-sample-source-lineage-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(NEW.sample_lineage_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF NEW.sample_lineage_sha256
                    IS DISTINCT FROM expected_sample_lineage_hash THEN
                RAISE EXCEPTION 'Phase 5 sample lineage hash mismatch';
            END IF;

            IF NEW.run_fingerprint_payload->>'policy_id'
                    IS DISTINCT FROM NEW.policy_id::text
               OR (NEW.run_fingerprint_payload->>'policy_version')::integer
                    IS DISTINCT FROM NEW.policy_version
               OR NEW.run_fingerprint_payload->>'policy_sha256'
                    IS DISTINCT FROM NEW.policy_sha256
               OR NEW.run_fingerprint_payload->>'mapping_id'
                    IS DISTINCT FROM NEW.mapping_id::text
               OR (NEW.run_fingerprint_payload->>'mapping_version')::integer
                    IS DISTINCT FROM NEW.mapping_version
               OR NEW.run_fingerprint_payload->>'mapping_input_sha256'
                    IS DISTINCT FROM NEW.mapping_input_sha256
               OR NEW.run_fingerprint_payload->>'fixture_id'
                    IS DISTINCT FROM NEW.fixture_id
               OR NEW.run_fingerprint_payload->>'fixture_sha256'
                    IS DISTINCT FROM NEW.fixture_sha256
               OR NEW.run_fingerprint_payload->>'snapshot_bundle_sha256'
                    IS DISTINCT FROM NEW.snapshot_bundle_sha256
               OR NEW.run_fingerprint_payload->>'code_version_git_sha'
                    IS DISTINCT FROM NEW.git_sha
               OR (NEW.run_fingerprint_payload->>'random_seed')::bigint
                    IS DISTINCT FROM NEW.random_seed THEN
                RAISE EXCEPTION 'Phase 5 run fingerprint does not bind server inputs';
            END IF;

            IF NEW.payload->>'request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.run_fingerprint_sha256
               OR NEW.payload->>'config_hash' IS DISTINCT FROM NEW.configuration_sha256
               OR NEW.payload->>'evaluation_policy_id'
                    IS DISTINCT FROM NEW.policy_id::text
               OR (NEW.payload->>'evaluation_policy_version')::integer
                    IS DISTINCT FROM NEW.policy_version
               OR NEW.payload->>'evaluation_policy_sha256'
                    IS DISTINCT FROM NEW.policy_sha256
               OR NEW.payload->>'mapping_id' IS DISTINCT FROM NEW.mapping_id::text
               OR (NEW.payload->>'mapping_version')::integer
                    IS DISTINCT FROM NEW.mapping_version
               OR NEW.payload->>'mapping_input_sha256'
                    IS DISTINCT FROM NEW.mapping_input_sha256
               OR NEW.payload->>'fixture_id' IS DISTINCT FROM NEW.fixture_id
               OR NEW.payload->>'fixture_sha256' IS DISTINCT FROM NEW.fixture_sha256
               OR NEW.payload->>'snapshot_bundle_sha256'
                    IS DISTINCT FROM NEW.snapshot_bundle_sha256
               OR NEW.payload->>'sample_lineage_sha256'
                    IS DISTINCT FROM NEW.sample_lineage_sha256
               OR NEW.payload->'source_observations'
                    IS DISTINCT FROM NEW.source_observations
               OR NEW.payload->'sample_lineage' IS DISTINCT FROM NEW.sample_lineage
               OR NEW.payload->>'code_version_git_sha' IS DISTINCT FROM NEW.git_sha
               OR (NEW.payload->>'random_seed')::bigint IS DISTINCT FROM NEW.random_seed
               OR (NEW.payload->>'raw_trial_count')::integer
                    IS DISTINCT FROM NEW.raw_trial_count
               OR (NEW.payload->>'effective_trial_count')::numeric
                    IS DISTINCT FROM NEW.effective_trial_count
               OR NEW.payload->>'promotion_state' IS DISTINCT FROM NEW.state
               OR jsonb_array_length(NEW.payload->'data_snapshots')
                    IS DISTINCT FROM NEW.expected_snapshot_count
               OR jsonb_array_length(NEW.payload->'source_observations')
                    IS DISTINCT FROM NEW.expected_source_observation_count
               OR jsonb_array_length(NEW.payload->'sample_lineage')
                    IS DISTINCT FROM NEW.expected_sample_lineage_count
               OR jsonb_array_length(NEW.payload->'trials')
                    IS DISTINCT FROM NEW.expected_trial_count
               OR jsonb_array_length(NEW.payload->'folds')
                    IS DISTINCT FROM NEW.expected_fold_count
               OR jsonb_array_length(NEW.payload->'preprocessing_fits')
                    IS DISTINCT FROM NEW.expected_preprocessing_fit_count
               OR jsonb_array_length(NEW.payload->'oos_ledger')
                    IS DISTINCT FROM NEW.expected_oos_ledger_count
               OR jsonb_array_length(NEW.payload->'cost_ledger')
                    IS DISTINCT FROM NEW.expected_cost_ledger_count
               OR jsonb_array_length(NEW.payload->'gates')
                    IS DISTINCT FROM NEW.expected_gate_result_count
               OR NEW.expected_preprocessing_fit_count
                    IS DISTINCT FROM NEW.expected_fold_count
               OR NEW.effective_trial_count_method
                    <> 'bailey-average-correlation-interpolation-v1' THEN
                RAISE EXCEPTION 'Phase 5 report columns are not bound by its frozen payload';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_reports_10_header
        BEFORE INSERT ON evaluation_reports
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_report_header()
        """
    )

    op.execute(
        """
        CREATE FUNCTION guard_phase5_expected_child_count()
        RETURNS trigger AS $$
        DECLARE
            expected_count integer;
            current_count integer;
            frozen_hash text;
            report_row evaluation_reports%ROWTYPE;
        BEGIN
            IF TG_TABLE_NAME = 'evaluation_feature_specs' THEN
                SELECT expected_feature_spec_count, policy_sha256
                INTO expected_count, frozen_hash
                FROM evaluation_policies
                WHERE policy_id = NEW.policy_id AND policy_version = NEW.policy_version
                FOR UPDATE;
                IF NOT FOUND OR NEW.policy_sha256 IS DISTINCT FROM frozen_hash THEN
                    RAISE EXCEPTION 'Phase 5 feature specification policy mismatch';
                END IF;
                SELECT count(*) INTO current_count
                FROM evaluation_feature_specs
                WHERE policy_id = NEW.policy_id AND policy_version = NEW.policy_version;
            ELSIF TG_TABLE_NAME = 'evaluation_label_specs' THEN
                SELECT expected_label_spec_count, policy_sha256
                INTO expected_count, frozen_hash
                FROM evaluation_policies
                WHERE policy_id = NEW.policy_id AND policy_version = NEW.policy_version
                FOR UPDATE;
                IF NOT FOUND OR NEW.policy_sha256 IS DISTINCT FROM frozen_hash THEN
                    RAISE EXCEPTION 'Phase 5 label specification policy mismatch';
                END IF;
                SELECT count(*) INTO current_count
                FROM evaluation_label_specs
                WHERE policy_id = NEW.policy_id AND policy_version = NEW.policy_version;
            ELSE
                SELECT * INTO report_row
                FROM evaluation_reports
                WHERE report_id = NEW.report_id
                FOR UPDATE;
                IF NOT FOUND OR NEW.report_sha256 IS DISTINCT FROM report_row.report_sha256 THEN
                    RAISE EXCEPTION 'Phase 5 child report lineage mismatch';
                END IF;

                expected_count := CASE TG_TABLE_NAME
                    WHEN 'evaluation_report_snapshots'
                        THEN report_row.expected_snapshot_count
                    WHEN 'evaluation_trials' THEN report_row.expected_trial_count
                    WHEN 'evaluation_folds' THEN report_row.expected_fold_count
                    WHEN 'evaluation_preprocessing_fits'
                        THEN report_row.expected_preprocessing_fit_count
                    WHEN 'evaluation_oos_ledger' THEN report_row.expected_oos_ledger_count
                    WHEN 'evaluation_cost_ledger' THEN report_row.expected_cost_ledger_count
                    WHEN 'evaluation_gate_results' THEN report_row.expected_gate_result_count
                    ELSE NULL
                END;
                IF expected_count IS NULL THEN
                    RAISE EXCEPTION 'Phase 5 expected-count guard called for unknown table';
                END IF;
                EXECUTE format(
                    'SELECT count(*) FROM %I WHERE report_id = $1',
                    TG_TABLE_NAME
                ) INTO current_count USING NEW.report_id;
            END IF;

            IF current_count >= expected_count THEN
                RAISE EXCEPTION 'Phase 5 child append exceeds frozen expected count';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (*PHASE5_POLICY_CHILD_TABLES, *PHASE5_REPORT_CHILD_TABLES):
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_expected_count
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION guard_phase5_expected_child_count()
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_report_snapshot()
        RETURNS trigger AS $$
        DECLARE
            report_mapping_id uuid;
            snapshot data_snapshots%ROWTYPE;
            manifest_hash text;
            expected_schema_versions jsonb;
        BEGIN
            SELECT mapping_id INTO report_mapping_id
            FROM evaluation_reports
            WHERE report_id = NEW.report_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 report snapshot has no report';
            END IF;

            SELECT * INTO snapshot
            FROM data_snapshots
            WHERE snapshot_id = NEW.snapshot_id
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 report snapshot is not persisted';
            END IF;
            SELECT snapshot_sha256 INTO manifest_hash
            FROM data_snapshot_manifests
            WHERE snapshot_id = NEW.snapshot_id;
            SELECT COALESCE(
                jsonb_agg(
                    to_jsonb(
                        (value->>'dataset_schema_id') || ':'
                        || (value->>'dataset_schema_version')
                    ) ORDER BY item_ordinal
                ),
                '[]'::jsonb
            ) INTO expected_schema_versions
            FROM jsonb_array_elements(snapshot.schema_bindings)
                WITH ORDINALITY AS item(value, item_ordinal);

            IF snapshot.mapping_id IS DISTINCT FROM report_mapping_id
               OR NOT snapshot.synthetic
               OR snapshot.snapshot_sha256 IS DISTINCT FROM NEW.snapshot_sha256
               OR snapshot.capability IS DISTINCT FROM NEW.capability
               OR snapshot.as_of_utc IS DISTINCT FROM NEW.as_of_utc
               OR snapshot.provider_id IS DISTINCT FROM NEW.provider_id
               OR snapshot.adapter_id IS DISTINCT FROM NEW.adapter_id
               OR snapshot.adapter_version IS DISTINCT FROM NEW.adapter_version
               OR snapshot.dataset_id IS DISTINCT FROM NEW.dataset_id
               OR snapshot.product_id IS DISTINCT FROM NEW.product_id
               OR snapshot.schema_bindings @> jsonb_build_array(jsonb_build_object(
                    'dataset_schema_id', NEW.dataset_schema_id,
                    'dataset_schema_version', NEW.dataset_schema_version
               )) IS NOT TRUE
               OR NEW.dataset_schema_versions IS DISTINCT FROM expected_schema_versions
               OR snapshot.quality_status IS DISTINCT FROM NEW.quality_status
               OR snapshot.fixture_set_version IS DISTINCT FROM NEW.fixture_set_version
               OR manifest_hash IS DISTINCT FROM NEW.snapshot_sha256 THEN
                RAISE EXCEPTION 'Phase 5 report snapshot lineage mismatch';
            END IF;
            IF NEW.payload->>'report_id' IS DISTINCT FROM NEW.report_id::text
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR NEW.payload#>>'{snapshot_evidence,snapshot_id}'
                    IS DISTINCT FROM NEW.snapshot_id::text
               OR NEW.payload#>>'{snapshot_evidence,snapshot_sha256}'
                    IS DISTINCT FROM NEW.snapshot_sha256
               OR NEW.payload#>>'{snapshot_evidence,capability}'
                    IS DISTINCT FROM NEW.capability
               OR NEW.payload#>>'{snapshot_evidence,provider_id}'
                    IS DISTINCT FROM NEW.provider_id
               OR NEW.payload#>>'{snapshot_evidence,adapter_id}'
                    IS DISTINCT FROM NEW.adapter_id
               OR NEW.payload#>>'{snapshot_evidence,adapter_version}'
                    IS DISTINCT FROM NEW.adapter_version
               OR NEW.payload#>>'{snapshot_evidence,dataset_id}'
                    IS DISTINCT FROM NEW.dataset_id
               OR NEW.payload#>>'{snapshot_evidence,product_id}'
                    IS DISTINCT FROM NEW.product_id
               OR NEW.payload#>'{snapshot_evidence,dataset_schema_versions}'
                    IS DISTINCT FROM NEW.dataset_schema_versions
               OR NEW.payload#>>'{snapshot_evidence,quality_status}'
                    IS DISTINCT FROM NEW.quality_status
               OR (NEW.payload#>>'{snapshot_evidence,as_of_utc}')::timestamptz
                    IS DISTINCT FROM NEW.as_of_utc
               OR NEW.payload#>>'{snapshot_evidence,fixture_set_version}'
                    IS DISTINCT FROM NEW.fixture_set_version THEN
                RAISE EXCEPTION 'Phase 5 snapshot evidence payload is not authoritative';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_report_snapshots_10_lineage
        BEFORE INSERT ON evaluation_report_snapshots
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_report_snapshot()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_preprocessing_fit_record()
        RETURNS trigger AS $$
        DECLARE
            fold_row evaluation_folds%ROWTYPE;
            report_row evaluation_reports%ROWTYPE;
            expected_train_ids_hash text;
            expected_fit_hash text;
            expected_fit_preimage jsonb;
            ordered_fit_values jsonb;
            derived_train_ids jsonb;
            fit_value_count integer;
            distinct_fit_value_count integer;
            invalid_fit_value_count integer;
            disallowed_fit_value_count integer;
            derived_mean numeric;
            derived_standard_deviation numeric;
        BEGIN
            SELECT * INTO fold_row
            FROM evaluation_folds
            WHERE report_id = NEW.report_id AND fold_id = NEW.fold_id;
            SELECT * INTO report_row
            FROM evaluation_reports
            WHERE report_id = NEW.report_id;
            IF NOT FOUND OR fold_row.fold_id IS NULL THEN
                RAISE EXCEPTION 'Phase 5 preprocessing fit has no frozen fold or report';
            END IF;

            IF NEW.payload->>'fit_sha256' IS DISTINCT FROM NEW.fit_sha256
               OR (NEW.payload->>'mean')::numeric IS DISTINCT FROM NEW.mean
               OR (NEW.payload->>'standard_deviation')::numeric
                    IS DISTINCT FROM NEW.standard_deviation
               OR (NEW.payload->>'ddof')::integer IS DISTINCT FROM NEW.ddof THEN
                RAISE EXCEPTION 'Phase 5 preprocessing statistics preimage mismatch';
            END IF;

            IF jsonb_typeof(NEW.record_payload->'train_sample_values') <> 'array'
               OR jsonb_array_length(NEW.record_payload->'train_sample_values')
                    IS DISTINCT FROM NEW.training_row_count
               OR NEW.record_payload->>'fold_sha256'
                    IS DISTINCT FROM fold_row.fold_sha256
               OR NEW.train_sample_ids IS DISTINCT FROM fold_row.payload->'train_sample_ids'
               OR NEW.training_row_count IS DISTINCT FROM fold_row.training_row_count
               OR NEW.ddof <> 1 THEN
                RAISE EXCEPTION
                    'Phase 5 preprocessing fit does not exactly match its frozen train fold';
            END IF;

            SELECT COALESCE(jsonb_agg(value_item ORDER BY value_item->>'sample_id'), '[]'),
                   COALESCE(
                       jsonb_agg(to_jsonb(value_item->>'sample_id')
                           ORDER BY value_item->>'sample_id'),
                       '[]'
                   ),
                   count(*),
                   count(DISTINCT value_item->>'sample_id'),
                   avg((value_item->>'value')::numeric(1000, 100)),
                   stddev_samp((value_item->>'value')::numeric(1000, 100))
            INTO ordered_fit_values, derived_train_ids, fit_value_count,
                 distinct_fit_value_count, derived_mean, derived_standard_deviation
            FROM jsonb_array_elements(NEW.record_payload->'train_sample_values')
                AS fit_value(value_item);
            IF NEW.record_payload->'train_sample_values' IS DISTINCT FROM ordered_fit_values
               OR NEW.train_sample_ids IS DISTINCT FROM derived_train_ids
               OR fit_value_count IS DISTINCT FROM NEW.training_row_count
               OR distinct_fit_value_count IS DISTINCT FROM NEW.training_row_count
               OR NEW.mean IS DISTINCT FROM round(derived_mean, 24)
               OR NEW.standard_deviation
                    IS DISTINCT FROM round(derived_standard_deviation, 24) THEN
                RAISE EXCEPTION
                    'Phase 5 preprocessing statistics are not derived from exact train values';
            END IF;

            SELECT count(*) INTO invalid_fit_value_count
            FROM jsonb_array_elements(NEW.record_payload->'train_sample_values')
                AS fit_value(value_item)
            LEFT JOIN LATERAL (
                SELECT lineage_item
                FROM jsonb_array_elements(report_row.sample_lineage)
                    AS lineage(lineage_item)
                WHERE lineage_item->>'sample_id' = value_item->>'sample_id'
            ) AS lineage ON TRUE
            WHERE lineage.lineage_item IS NULL
               OR value_item->>'sample_sha256'
                    IS DISTINCT FROM lineage.lineage_item->>'sample_sha256'
               OR (value_item->>'value')::numeric IS DISTINCT FROM
                    (lineage.lineage_item#>>'{feature_derivation,derived_feature_value}')::numeric;

            SELECT count(*) INTO disallowed_fit_value_count
            FROM jsonb_array_elements_text(NEW.train_sample_ids) AS fit_id(sample_id)
            WHERE sample_id IN (
                SELECT jsonb_array_elements_text(fold_row.payload->'test_sample_ids')
                UNION ALL
                SELECT jsonb_array_elements_text(fold_row.payload->'purged_sample_ids')
                UNION ALL
                SELECT jsonb_array_elements_text(fold_row.payload->'embargoed_sample_ids')
            );
            IF invalid_fit_value_count <> 0 OR disallowed_fit_value_count <> 0 THEN
                RAISE EXCEPTION
                    'Phase 5 preprocessing fit contains unknown or disallowed sample evidence';
            END IF;

            IF btrim(NEW.record_payload->>'train_sample_ids_canonical_json') = ''
               OR (NEW.record_payload->>'train_sample_ids_canonical_json')::jsonb
                    IS DISTINCT FROM NEW.train_sample_ids THEN
                RAISE EXCEPTION 'Phase 5 preprocessing train-id canonical preimage mismatch';
            END IF;
            expected_train_ids_hash := encode(
                sha256(
                    convert_to('phase5-preprocessing-train-ids-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(
                        NEW.record_payload->>'train_sample_ids_canonical_json',
                        'UTF8'
                    )
                ),
                'hex'
            );
            IF NEW.train_sample_ids_sha256 IS DISTINCT FROM expected_train_ids_hash THEN
                RAISE EXCEPTION 'Phase 5 preprocessing train-id hash mismatch';
            END IF;

            expected_fit_preimage := NEW.record_payload
                - 'fit_id'
                - 'fit_sha256'
                - 'train_sample_ids_canonical_json'
                - 'fit_preimage_canonical_json'
                - 'statistics_sha256';
            IF btrim(NEW.record_payload->>'fit_preimage_canonical_json') = ''
               OR (NEW.record_payload->>'fit_preimage_canonical_json')::jsonb
                    IS DISTINCT FROM expected_fit_preimage THEN
                RAISE EXCEPTION 'Phase 5 preprocessing fit canonical preimage mismatch';
            END IF;
            expected_fit_hash := encode(
                sha256(
                    convert_to('phase5-train-only-fit-record-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(
                        NEW.record_payload->>'fit_preimage_canonical_json',
                        'UTF8'
                    )
                ),
                'hex'
            );
            IF NEW.fit_sha256 IS DISTINCT FROM expected_fit_hash THEN
                RAISE EXCEPTION 'Phase 5 preprocessing fit semantic hash mismatch';
            END IF;

            IF NEW.record_payload->>'fit_id' IS DISTINCT FROM NEW.fit_id::text
               OR NEW.record_payload->>'fit_sha256' IS DISTINCT FROM NEW.fit_sha256
               OR NEW.record_payload->>'fold_id' IS DISTINCT FROM NEW.fold_id::text
               OR NEW.record_payload->>'transformer_id'
                    IS DISTINCT FROM NEW.transformer_id
               OR NEW.record_payload->>'transformer_version'
                    IS DISTINCT FROM NEW.transformer_version
               OR NEW.record_payload->>'fold_sha256'
                    IS DISTINCT FROM fold_row.fold_sha256
               OR NEW.record_payload->'train_sample_values'
                    IS DISTINCT FROM ordered_fit_values
               OR NEW.record_payload->'train_sample_ids'
                    IS DISTINCT FROM NEW.train_sample_ids
               OR NEW.record_payload->>'train_sample_ids_sha256'
                    IS DISTINCT FROM NEW.train_sample_ids_sha256
               OR (NEW.record_payload->>'mean')::numeric IS DISTINCT FROM NEW.mean
               OR (NEW.record_payload->>'standard_deviation')::numeric
                    IS DISTINCT FROM NEW.standard_deviation
               OR (NEW.record_payload->>'ddof')::integer IS DISTINCT FROM NEW.ddof
               OR NEW.record_payload->>'statistics_sha256'
                    IS DISTINCT FROM NEW.statistics_sha256 THEN
                RAISE EXCEPTION 'Phase 5 preprocessing full-record payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_preprocessing_fits_10_record
        BEFORE INSERT ON evaluation_preprocessing_fits
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_preprocessing_fit_record()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_trial_return_calendar()
        RETURNS trigger AS $$
        DECLARE
            status_value text;
            return_value jsonb;
            timestamp_value text;
            previous_return_timestamp timestamptz;
            current_return_timestamp timestamptz;
            computed_observation_count integer := 0;
            computed_missing_count integer := 0;
            computed_no_trade_count integer := 0;
        BEGIN
            FOR status_value, return_value, timestamp_value IN
                SELECT status_item.value, return_item.value, timestamp_item.value
                FROM jsonb_array_elements_text(NEW.return_statuses)
                    WITH ORDINALITY AS status_item(value, ordinal)
                JOIN jsonb_array_elements(NEW.net_returns)
                    WITH ORDINALITY AS return_item(value, ordinal) USING (ordinal)
                JOIN jsonb_array_elements_text(NEW.return_timestamps_utc)
                    WITH ORDINALITY AS timestamp_item(value, ordinal) USING (ordinal)
                ORDER BY ordinal
            LOOP
                computed_observation_count := computed_observation_count + 1;
                current_return_timestamp := timestamp_value::timestamptz;
                IF previous_return_timestamp IS NOT NULL
                   AND current_return_timestamp <= previous_return_timestamp THEN
                    RAISE EXCEPTION
                        'Phase 5 trial return timestamps must be unique and chronological';
                END IF;
                previous_return_timestamp := current_return_timestamp;

                IF status_value = 'missing' THEN
                    computed_missing_count := computed_missing_count + 1;
                    IF return_value IS DISTINCT FROM 'null'::jsonb THEN
                        RAISE EXCEPTION
                            'Phase 5 missing trial return must retain a null value';
                    END IF;
                ELSE
                    IF return_value = 'null'::jsonb THEN
                        RAISE EXCEPTION
                            'Phase 5 non-missing trial return requires a value';
                    END IF;
                    IF status_value = 'no_trade' THEN
                        computed_no_trade_count := computed_no_trade_count + 1;
                        IF (return_value #>> '{}')::numeric <> 0 THEN
                            RAISE EXCEPTION
                                'Phase 5 no-trade trial return must be exact zero';
                        END IF;
                    ELSE
                        PERFORM (return_value #>> '{}')::numeric;
                    END IF;
                END IF;
            END LOOP;

            IF computed_observation_count IS DISTINCT FROM NEW.return_observation_count
               OR computed_missing_count IS DISTINCT FROM NEW.missing_return_count
               OR computed_no_trade_count IS DISTINCT FROM NEW.no_trade_count THEN
                RAISE EXCEPTION 'Phase 5 trial return-status counts are not exact';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_trials_07_return_calendar
        BEFORE INSERT ON evaluation_trials
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_trial_return_calendar()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_child_payload_columns()
        RETURNS trigger AS $$
        DECLARE
            row_value jsonb;
            report_config_hash text;
            report_policy_sha256 text;
            expected_trial_config_hash text;
        BEGIN
            row_value := to_jsonb(NEW);
            SELECT configuration_sha256, policy_sha256
            INTO report_config_hash, report_policy_sha256
            FROM evaluation_reports
            WHERE report_id = NEW.report_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 child payload has no report';
            END IF;

            IF (NEW.payload->>'ordinal')::integer
                    IS DISTINCT FROM (row_value->>'ordinal')::integer THEN
                RAISE EXCEPTION 'Phase 5 child payload ordinal mismatch';
            END IF;

            IF TG_TABLE_NAME = 'evaluation_trials' THEN
                expected_trial_config_hash := encode(
                    sha256(
                        convert_to('phase5-evaluation-config-v1', 'UTF8')
                        || decode('00', 'hex')
                        || convert_to(NEW.config_canonical_json, 'UTF8')
                    ),
                    'hex'
                );
                IF NEW.payload->>'trial_key' IS DISTINCT FROM row_value->>'trial_key'
                   OR NEW.payload->>'strategy_family'
                        IS DISTINCT FROM row_value->>'strategy_family'
                   OR NEW.payload->>'selection_scope'
                        IS DISTINCT FROM row_value->>'selection_scope'
                   OR NEW.payload->>'initiated_by' IS DISTINCT FROM row_value->>'initiated_by'
                   OR (NEW.payload->>'initiated_at_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'initiated_at_utc')::timestamptz
                   OR NEW.payload->>'config_sha256'
                        IS DISTINCT FROM row_value->>'config_sha256'
                   OR NEW.payload->'config_preimage'
                        IS DISTINCT FROM NEW.config_preimage
                   OR NEW.config_sha256 IS DISTINCT FROM expected_trial_config_hash
                   OR NEW.payload->'configuration'
                        IS DISTINCT FROM row_value->'configuration'
                   OR NEW.payload->>'policy_sha256'
                        IS DISTINCT FROM report_policy_sha256
                   OR NEW.payload->>'status' IS DISTINCT FROM row_value->>'status'
                   OR NEW.payload->>'oos_return_state'
                        IS DISTINCT FROM NEW.oos_return_state
                   OR NEW.payload->'net_returns' IS DISTINCT FROM NEW.net_returns
                   OR NEW.payload->'return_statuses' IS DISTINCT FROM NEW.return_statuses
                   OR NEW.payload->'return_timestamps_utc'
                        IS DISTINCT FROM NEW.return_timestamps_utc
                   OR NEW.payload->>'failure_reason'
                        IS DISTINCT FROM row_value->>'failure_reason' THEN
                    RAISE EXCEPTION 'Phase 5 trial columns differ from hash preimage';
                END IF;
            ELSIF TG_TABLE_NAME = 'evaluation_folds' THEN
                IF NEW.payload->>'fold_kind' IS DISTINCT FROM row_value->>'fold_kind'
                   OR NEW.payload->>'parent_fold_id'
                        IS DISTINCT FROM row_value->>'parent_fold_id'
                   OR (NEW.payload->>'train_start_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'train_start_utc')::timestamptz
                   OR (NEW.payload->>'train_end_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'train_end_utc')::timestamptz
                   OR (NEW.payload->>'test_start_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'test_start_utc')::timestamptz
                   OR (NEW.payload->>'test_end_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'test_end_utc')::timestamptz
                   OR jsonb_array_length(NEW.payload->'train_sample_ids')
                        IS DISTINCT FROM (row_value->>'training_row_count')::integer
                   OR jsonb_array_length(NEW.payload->'purged_sample_ids')
                        IS DISTINCT FROM (row_value->>'purged_row_count')::integer
                   OR jsonb_array_length(NEW.payload->'test_sample_ids')
                        IS DISTINCT FROM (row_value->>'test_row_count')::integer
                   OR jsonb_array_length(NEW.payload->'embargoed_sample_ids')
                        IS DISTINCT FROM (row_value->>'embargoed_row_count')::integer
                   OR (NEW.payload->>'embargo_duration_seconds')::bigint
                        IS DISTINCT FROM (row_value->>'embargo_duration_seconds')::bigint
                   OR (NEW.payload->>'embargo_applied')::boolean
                        IS DISTINCT FROM (row_value->>'embargo_applied')::boolean THEN
                    RAISE EXCEPTION 'Phase 5 fold columns differ from hash preimage';
                END IF;
            ELSIF TG_TABLE_NAME = 'evaluation_oos_ledger' THEN
                IF NEW.payload->>'trial_id' IS DISTINCT FROM row_value->>'trial_id'
                   OR NEW.payload->>'fold_id' IS DISTINCT FROM row_value->>'fold_id'
                   OR NEW.payload->>'sample_id' IS DISTINCT FROM row_value->>'sample_id'
                   OR NEW.payload->>'sample_sha256'
                        IS DISTINCT FROM row_value->>'sample_sha256'
                   OR NEW.payload->'source_observation_refs'
                        IS DISTINCT FROM NEW.source_observation_refs
                   OR (NEW.payload->>'information_start_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'information_start_utc')::timestamptz
                   OR (NEW.payload->>'information_end_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'information_end_utc')::timestamptz
                   OR (NEW.payload->>'decision_time_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'decision_time_utc')::timestamptz
                   OR (NEW.payload->>'label_t0_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'label_t0_utc')::timestamptz
                   OR (NEW.payload->>'label_t1_utc')::timestamptz
                        IS DISTINCT FROM (row_value->>'label_t1_utc')::timestamptz
                   OR (NEW.payload->>'predicted_value')::numeric
                        IS DISTINCT FROM (row_value->>'prediction_value')::numeric
                   OR (NEW.payload->>'gross_return')::numeric
                        IS DISTINCT FROM (row_value->>'gross_return')::numeric
                   OR (NEW.payload->>'baseline_net_return')::numeric
                        IS DISTINCT FROM (row_value->>'baseline_net_return')::numeric
                   OR NEW.payload->>'return_status'
                        IS DISTINCT FROM row_value->>'return_status'
                   OR (NEW.payload->>'delisting_return_handled')::boolean
                        IS DISTINCT FROM (row_value->>'delisting_return_handled')::boolean THEN
                    RAISE EXCEPTION 'Phase 5 OOS columns differ from hash preimage';
                END IF;
            ELSIF TG_TABLE_NAME = 'evaluation_cost_ledger' THEN
                IF NEW.payload->>'sample_id' IS DISTINCT FROM row_value->>'sample_id'
                   OR NEW.payload->>'scenario' IS DISTINCT FROM row_value->>'scenario'
                   OR NEW.payload->>'allocation_input_sha256'
                        IS DISTINCT FROM row_value->>'allocation_input_sha256'
                   OR NEW.payload->>'return_status'
                        IS DISTINCT FROM row_value->>'return_status'
                   OR (NEW.payload->>'requested_quantity')::numeric
                        IS DISTINCT FROM (row_value->>'requested_quantity')::numeric
                   OR (NEW.payload->>'filled_quantity')::numeric
                        IS DISTINCT FROM (row_value->>'filled_quantity')::numeric
                   OR (NEW.payload->>'rejected_quantity')::numeric
                        IS DISTINCT FROM (row_value->>'rejected_quantity')::numeric
                   OR (NEW.payload->>'unfilled_quantity')::numeric
                        IS DISTINCT FROM (row_value->>'unfilled_quantity')::numeric
                   OR NEW.payload->>'fill_status' IS DISTINCT FROM row_value->>'fill_status'
                   OR (NEW.payload->>'hard_to_borrow_available')::boolean
                        IS DISTINCT FROM (row_value->>'hard_to_borrow_available')::boolean
                   OR (NEW.payload->>'gross_return')::numeric
                        IS DISTINCT FROM (row_value->>'gross_return')::numeric
                   OR (NEW.payload->>'fee_cost')::numeric
                        IS DISTINCT FROM (row_value->>'fee_cost')::numeric
                   OR (NEW.payload->>'spread_cost')::numeric
                        IS DISTINCT FROM (row_value->>'spread_cost')::numeric
                   OR (NEW.payload->>'impact_cost')::numeric
                        IS DISTINCT FROM (row_value->>'impact_cost')::numeric
                   OR (NEW.payload->>'latency_cost')::numeric
                        IS DISTINCT FROM (row_value->>'latency_cost')::numeric
                   OR (NEW.payload->>'borrow_cost')::numeric
                        IS DISTINCT FROM (row_value->>'borrow_cost')::numeric
                   OR (NEW.payload->>'capacity_cost')::numeric
                        IS DISTINCT FROM (row_value->>'capacity_cost')::numeric
                   OR (NEW.payload->>'total_cost')::numeric
                        IS DISTINCT FROM (row_value->>'total_cost')::numeric
                   OR (NEW.payload->>'net_return')::numeric
                        IS DISTINCT FROM (row_value->>'net_return')::numeric
                   OR (NEW.payload->>'participation_rate')::numeric
                        IS DISTINCT FROM (row_value->>'participation_rate')::numeric
                   OR (NEW.payload->>'capacity_breached')::boolean
                        IS DISTINCT FROM (row_value->>'capacity_breached')::boolean THEN
                    RAISE EXCEPTION 'Phase 5 cost columns differ from hash preimage';
                END IF;
            ELSIF TG_TABLE_NAME = 'evaluation_gate_results' THEN
                IF NEW.payload->>'config_hash' IS DISTINCT FROM report_config_hash
                   OR row_value->>'config_hash' IS DISTINCT FROM report_config_hash
                   OR NEW.payload->>'gate_code' IS DISTINCT FROM row_value->>'gate_code'
                   OR NEW.payload->>'outcome' IS DISTINCT FROM row_value->>'outcome'
                   OR NEW.payload->'reason_codes'
                        IS DISTINCT FROM row_value->'reason_codes' THEN
                    RAISE EXCEPTION 'Phase 5 gate columns differ from hash preimage';
                END IF;
            ELSE
                RAISE EXCEPTION 'Phase 5 child payload validator called for unknown table';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (
        "evaluation_trials",
        "evaluation_folds",
        "evaluation_oos_ledger",
        "evaluation_cost_ledger",
        "evaluation_gate_results",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_10_payload_columns
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase5_child_payload_columns()
            """
        )

    op.execute(
        """
        CREATE FUNCTION phase5_exact_ordinals(
            checked_table regclass,
            parent_column text,
            parent_id uuid,
            expected_count integer
        )
        RETURNS boolean AS $$
        DECLARE
            actual_count integer;
            minimum_ordinal integer;
            maximum_ordinal integer;
        BEGIN
            EXECUTE format(
                'SELECT count(*), min(ordinal), max(ordinal) FROM %s WHERE %I = $1',
                checked_table,
                parent_column
            ) INTO actual_count, minimum_ordinal, maximum_ordinal USING parent_id;
            RETURN actual_count = expected_count
                AND ((expected_count = 0
                      AND minimum_ordinal IS NULL
                      AND maximum_ordinal IS NULL)
                     OR (expected_count > 0
                         AND minimum_ordinal = 0
                         AND maximum_ordinal = expected_count - 1));
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE FUNCTION phase5_exact_policy_ordinals(
            checked_table regclass,
            checked_policy_id uuid,
            checked_policy_version integer,
            expected_count integer
        )
        RETURNS boolean AS $$
        DECLARE
            actual_count integer;
            minimum_ordinal integer;
            maximum_ordinal integer;
        BEGIN
            EXECUTE format(
                'SELECT count(*), min(ordinal), max(ordinal) '
                'FROM %s WHERE policy_id = $1 AND policy_version = $2',
                checked_table
            ) INTO actual_count, minimum_ordinal, maximum_ordinal
              USING checked_policy_id, checked_policy_version;
            RETURN actual_count = expected_count
                AND ((expected_count = 0
                      AND minimum_ordinal IS NULL
                      AND maximum_ordinal IS NULL)
                     OR (expected_count > 0
                         AND minimum_ordinal = 0
                         AND maximum_ordinal = expected_count - 1));
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_policy_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_policy_id uuid;
            checked_policy_version integer;
            policy evaluation_policies%ROWTYPE;
            actual_feature_hashes jsonb;
            actual_label_hashes jsonb;
            actual_feature_specification jsonb;
            actual_label_specification jsonb;
        BEGIN
            checked_policy_id := NEW.policy_id;
            checked_policy_version := NEW.policy_version;
            SELECT * INTO policy FROM evaluation_policies
            WHERE policy_id = checked_policy_id
              AND policy_version = checked_policy_version;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 policy completeness target is missing';
            END IF;

            IF NOT phase5_exact_policy_ordinals(
                    'evaluation_feature_specs'::regclass,
                    checked_policy_id,
                    checked_policy_version,
                    policy.expected_feature_spec_count
                )
               OR NOT phase5_exact_policy_ordinals(
                    'evaluation_label_specs'::regclass,
                    checked_policy_id,
                    checked_policy_version,
                    policy.expected_label_spec_count
               ) THEN
                RAISE EXCEPTION 'Phase 5 policy has incomplete specification counts';
            END IF;

            SELECT COALESCE(
                jsonb_agg(to_jsonb(feature_spec_sha256) ORDER BY ordinal),
                '[]'::jsonb
            ) INTO actual_feature_hashes
            FROM evaluation_feature_specs
            WHERE policy_id = checked_policy_id
              AND policy_version = checked_policy_version;
            SELECT COALESCE(
                jsonb_agg(to_jsonb(label_spec_sha256) ORDER BY ordinal),
                '[]'::jsonb
            ) INTO actual_label_hashes
            FROM evaluation_label_specs
            WHERE policy_id = checked_policy_id
              AND policy_version = checked_policy_version;

            IF policy.feature_spec_hashes IS DISTINCT FROM actual_feature_hashes
               OR policy.label_spec_hashes IS DISTINCT FROM actual_label_hashes THEN
                RAISE EXCEPTION 'Phase 5 frozen policy specification hashes mismatch';
            END IF;
            SELECT payload || jsonb_build_object(
                'feature_specification_id', feature_spec_id::text,
                'content_sha256', feature_spec_sha256
            ) INTO actual_feature_specification
            FROM evaluation_feature_specs
            WHERE policy_id = checked_policy_id
              AND policy_version = checked_policy_version;
            SELECT payload || jsonb_build_object(
                'label_specification_id', label_spec_id::text,
                'content_sha256', label_spec_sha256
            ) INTO actual_label_specification
            FROM evaluation_label_specs
            WHERE policy_id = checked_policy_id
              AND policy_version = checked_policy_version;
            IF policy.payload->'feature_specification'
                    IS DISTINCT FROM actual_feature_specification
               OR policy.payload->'label_specification'
                    IS DISTINCT FROM actual_label_specification THEN
                RAISE EXCEPTION 'Phase 5 policy payload differs from persisted specifications';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER evaluation_policies_complete
        AFTER INSERT ON evaluation_policies
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_policy_completeness()
        """
    )
    for table in PHASE5_POLICY_CHILD_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_policy_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase5_policy_completeness()
            """
        )

    op.execute(
        """
        CREATE FUNCTION phase5_json_payload_equivalent(left_value jsonb, right_value jsonb)
        RETURNS boolean AS $$
        DECLARE
            object_key text;
            left_keys text[];
            right_keys text[];
            item_index integer;
            left_text text;
            right_text text;
            timestamp_pattern constant text :=
                '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
                '([.][0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$';
        BEGIN
            IF jsonb_typeof(left_value) IS DISTINCT FROM jsonb_typeof(right_value) THEN
                RETURN FALSE;
            END IF;
            IF left_value IS NOT DISTINCT FROM right_value THEN
                RETURN TRUE;
            END IF;
            IF jsonb_typeof(left_value) = 'object' THEN
                SELECT array_agg(key ORDER BY key) INTO left_keys
                FROM jsonb_object_keys(left_value) AS item(key);
                SELECT array_agg(key ORDER BY key) INTO right_keys
                FROM jsonb_object_keys(right_value) AS item(key);
                IF left_keys IS DISTINCT FROM right_keys THEN
                    RETURN FALSE;
                END IF;
                FOREACH object_key IN ARRAY left_keys
                LOOP
                    IF NOT phase5_json_payload_equivalent(
                        left_value->object_key,
                        right_value->object_key
                    ) THEN
                        RETURN FALSE;
                    END IF;
                END LOOP;
                RETURN TRUE;
            ELSIF jsonb_typeof(left_value) = 'array' THEN
                IF jsonb_array_length(left_value) <> jsonb_array_length(right_value) THEN
                    RETURN FALSE;
                END IF;
                IF jsonb_array_length(left_value) = 0 THEN
                    RETURN TRUE;
                END IF;
                FOR item_index IN 0..jsonb_array_length(left_value) - 1
                LOOP
                    IF NOT phase5_json_payload_equivalent(
                        left_value->item_index,
                        right_value->item_index
                    ) THEN
                        RETURN FALSE;
                    END IF;
                END LOOP;
                RETURN TRUE;
            ELSIF jsonb_typeof(left_value) = 'string' THEN
                left_text := left_value #>> '{}';
                right_text := right_value #>> '{}';
                IF left_text ~ timestamp_pattern AND right_text ~ timestamp_pattern THEN
                    RETURN left_text::timestamptz = right_text::timestamptz;
                END IF;
            END IF;
            RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_report_source_lineage(checked_report_id uuid)
        RETURNS void AS $$
        DECLARE
            report_row evaluation_reports%ROWTYPE;
            sorted_source_observations jsonb;
            sorted_sample_lineage jsonb;
            distinct_source_count integer;
            distinct_sample_count integer;
            invalid_source_count integer;
            invalid_lineage_count integer;
            invalid_lineage_ref_count integer;
            invalid_lineage_capability_count integer;
            unused_source_count integer;
            invalid_derivation_count integer;
            invalid_membership_count integer;
            invalid_oos_lineage_count integer;
            required_capabilities jsonb;
        BEGIN
            SELECT * INTO report_row
            FROM evaluation_reports WHERE report_id = checked_report_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 source-lineage report is missing';
            END IF;
            SELECT required_snapshot_capabilities INTO required_capabilities
            FROM evaluation_policies
            WHERE policy_id = report_row.policy_id
              AND policy_version = report_row.policy_version;
            IF required_capabilities IS NULL THEN
                RAISE EXCEPTION 'Phase 5 source-lineage policy is missing';
            END IF;

            IF jsonb_array_length(report_row.source_observations)
                    IS DISTINCT FROM report_row.expected_source_observation_count
               OR jsonb_array_length(report_row.sample_lineage)
                    IS DISTINCT FROM report_row.expected_sample_lineage_count THEN
                RAISE EXCEPTION 'Phase 5 source-lineage counts are not exact';
            END IF;

            SELECT COALESCE(
                jsonb_agg(
                    source_item ORDER BY
                    source_item#>>'{key,capability}',
                    source_item#>>'{key,normalized_observation_id}'
                ),
                '[]'::jsonb
            ) INTO sorted_source_observations
            FROM jsonb_array_elements(report_row.source_observations)
                AS source(source_item);
            SELECT count(DISTINCT jsonb_build_array(
                source_item#>>'{key,capability}',
                source_item#>>'{normalized_observation,snapshot_id}',
                source_item#>>'{key,normalized_observation_id}'
            )) INTO distinct_source_count
            FROM jsonb_array_elements(report_row.source_observations)
                AS source(source_item);
            IF report_row.source_observations IS DISTINCT FROM sorted_source_observations
               OR distinct_source_count
                    IS DISTINCT FROM report_row.expected_source_observation_count THEN
                RAISE EXCEPTION
                    'Phase 5 source observations must be unique and canonically sorted';
            END IF;

            SELECT count(*) INTO invalid_source_count
            FROM jsonb_array_elements(report_row.source_observations)
                AS source(source_item)
            LEFT JOIN evaluation_report_snapshots AS binding
              ON binding.report_id = checked_report_id
             AND binding.capability = source_item#>>'{key,capability}'
             AND binding.snapshot_id =
                    (source_item#>>'{normalized_observation,snapshot_id}')::uuid
             AND binding.snapshot_sha256 =
                    source_item#>>'{normalized_observation,snapshot_sha256}'
            LEFT JOIN data_snapshots AS snapshot
              ON snapshot.snapshot_id = binding.snapshot_id
             AND snapshot.snapshot_sha256 = binding.snapshot_sha256
            LEFT JOIN data_normalized_observations AS observation
              ON observation.snapshot_id = binding.snapshot_id
             AND observation.normalized_observation_id =
                    (source_item#>>'{key,normalized_observation_id}')::uuid
            LEFT JOIN data_snapshot_constituents AS constituent
              ON constituent.snapshot_id = observation.snapshot_id
             AND constituent.normalized_observation_id =
                    observation.normalized_observation_id
             AND constituent.raw_observation_id = observation.raw_observation_id
             AND constituent.observation_revision_id = observation.observation_revision_id
            WHERE binding.report_snapshot_id IS NULL
               OR snapshot.snapshot_id IS NULL
               OR observation.normalized_observation_id IS NULL
               OR constituent.normalized_observation_id IS NULL
               OR source_item->>'schema_version'
                    IS DISTINCT FROM 'phase5-resolved-source-observation-v1'
               OR source_item#>>'{key,normalized_observation_id}'
                    IS DISTINCT FROM
                        source_item#>>'{normalized_observation,normalized_observation_id}'
               OR source_item#>>'{normalized_observation,snapshot_sha256}'
                    IS DISTINCT FROM observation.snapshot_sha256
               OR (source_item#>>'{normalized_observation,raw_observation_id}')::uuid
                    IS DISTINCT FROM observation.raw_observation_id
               OR (source_item#>>'{normalized_observation,observation_revision_id}')::uuid
                    IS DISTINCT FROM observation.observation_revision_id
               OR source_item#>>'{normalized_observation,normalized_content_sha256}'
                    IS DISTINCT FROM observation.normalized_content_sha256
               OR source_item#>>'{normalized_observation,raw_payload_sha256}'
                    IS DISTINCT FROM observation.raw_payload_sha256
               OR source_item->>'disposition' IS DISTINCT FROM constituent.disposition
               OR constituent.disposition NOT IN (
                    'included_as_of','retained_historical_vintage','explicit_missingness'
               )
               OR constituent.snapshot_sha256 IS DISTINCT FROM observation.snapshot_sha256
               OR constituent.normalized_content_sha256
                    IS DISTINCT FROM observation.normalized_content_sha256
               OR constituent.raw_payload_sha256 IS DISTINCT FROM observation.raw_payload_sha256
               OR constituent.record_type IS DISTINCT FROM observation.payload->>'record_type'
               OR NOT phase5_json_payload_equivalent(
                    source_item#>'{normalized_observation,payload}',
                    observation.payload
               )
               OR source_item#>>'{normalized_observation,envelope_schema_version}'
                    IS DISTINCT FROM observation.envelope_schema_version
               OR source_item#>>'{normalized_observation,logical_record_id}'
                    IS DISTINCT FROM observation.logical_record_id
               OR source_item#>>'{normalized_observation,logical_record_key_sha256}'
                    IS DISTINCT FROM observation.logical_record_key_sha256
               OR source_item#>>'{normalized_observation,provider_id}'
                    IS DISTINCT FROM observation.provider_id
               OR source_item#>>'{normalized_observation,adapter_id}'
                    IS DISTINCT FROM observation.adapter_id
               OR source_item#>>'{normalized_observation,adapter_version}'
                    IS DISTINCT FROM observation.adapter_version
               OR source_item#>>'{normalized_observation,dataset_id}'
                    IS DISTINCT FROM observation.dataset_id
               OR source_item#>>'{normalized_observation,product_id}'
                    IS DISTINCT FROM observation.product_id
               OR source_item#>>'{normalized_observation,dataset_schema_id}'
                    IS DISTINCT FROM observation.dataset_schema_id
               OR source_item#>>'{normalized_observation,dataset_schema_version}'
                    IS DISTINCT FROM observation.dataset_schema_version
               OR source_item#>>'{normalized_observation,entitlement_id}'
                    IS DISTINCT FROM observation.entitlement_id
               OR source_item#>>'{normalized_observation,use_rights_id}'
                    IS DISTINCT FROM observation.use_rights_id
               OR source_item#>>'{normalized_observation,source_record_id}'
                    IS DISTINCT FROM observation.source_record_id
               OR (source_item#>>'{normalized_observation,instrument_id}')::uuid
                    IS DISTINCT FROM observation.instrument_id
               OR (source_item#>>'{normalized_observation,listing_id}')::uuid
                    IS DISTINCT FROM observation.listing_id
               OR (source_item#>>'{normalized_observation,event_time}')::timestamptz
                    IS DISTINCT FROM observation.event_time
               OR (source_item#>>'{normalized_observation,available_at}')::timestamptz
                    IS DISTINCT FROM observation.available_at
               OR (source_item#>>'{normalized_observation,retrieved_at}')::timestamptz
                    IS DISTINCT FROM observation.retrieved_at
               OR (source_item#>>'{normalized_observation,valid_from}')::timestamptz
                    IS DISTINCT FROM observation.valid_from
               OR (source_item#>>'{normalized_observation,valid_to}')::timestamptz
                    IS DISTINCT FROM observation.valid_to
               OR source_item#>>'{normalized_observation,revision_id}'
                    IS DISTINCT FROM observation.revision_id
               OR source_item#>>'{normalized_observation,vintage_id}'
                    IS DISTINCT FROM observation.vintage_id
               OR source_item#>>'{normalized_observation,source_timezone}'
                    IS DISTINCT FROM observation.source_timezone
               OR source_item#>>'{normalized_observation,calendar_id}'
                    IS DISTINCT FROM observation.calendar_id
               OR source_item#>>'{normalized_observation,unit}'
                    IS DISTINCT FROM observation.unit
               OR source_item#>>'{normalized_observation,currency}'
                    IS DISTINCT FROM observation.currency
               OR source_item#>>'{normalized_observation,availability_precision}'
                    IS DISTINCT FROM observation.availability_precision
               OR source_item#>>'{normalized_observation,availability_convention}'
                    IS DISTINCT FROM observation.availability_convention
               OR (source_item#>>'{normalized_observation,availability_source_date}')::date
                    IS DISTINCT FROM observation.availability_source_date
               OR source_item#>'{normalized_observation,quality_flags}'
                    IS DISTINCT FROM observation.quality_flags
               OR source_item#>'{normalized_observation,field_missingness}'
                    IS DISTINCT FROM observation.field_missingness;
            IF invalid_source_count <> 0 THEN
                RAISE EXCEPTION
                    'Phase 5 source observation differs from immutable Phase 4 evidence';
            END IF;

            SELECT COALESCE(
                jsonb_agg(lineage_item ORDER BY lineage_item->>'sample_id'),
                '[]'::jsonb
            ) INTO sorted_sample_lineage
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item);
            SELECT count(DISTINCT lineage_item->>'sample_id')
            INTO distinct_sample_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item);
            IF report_row.sample_lineage IS DISTINCT FROM sorted_sample_lineage
               OR distinct_sample_count
                    IS DISTINCT FROM report_row.expected_sample_lineage_count THEN
                RAISE EXCEPTION
                    'Phase 5 sample lineage must be unique and canonically sorted';
            END IF;

            SELECT count(*) INTO invalid_lineage_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            WHERE btrim(lineage_item->>'sample_id') = ''
               OR lineage_item->>'sample_sha256' !~ '^[0-9a-f]{64}$'
               OR lineage_item->>'feature_available_at_utc' IS NULL
               OR jsonb_typeof(lineage_item->'feature_derivation') <> 'object'
               OR jsonb_typeof(lineage_item->'dependency_graph') <> 'object'
               OR lineage_item#>>'{dependency_graph,schema_version}'
                    IS DISTINCT FROM 'phase5-derived-dependency-graph-v1'
               OR lineage_item#>>'{dependency_graph,graph_sha256}' !~ '^[0-9a-f]{64}$'
               OR jsonb_typeof(lineage_item->'membership_source_observation_key')
                    <> 'object'
               OR lineage_item#>>'{membership_source_observation_key,capability}'
                    IS DISTINCT FROM 'universe_membership'
               OR jsonb_typeof(lineage_item->'source_observation_refs') <> 'array'
               OR jsonb_array_length(lineage_item->'source_observation_refs') < 1
               OR lineage_item->>'synthetic_ledger_value_rule'
                    IS DISTINCT FROM 'deterministic-synthetic-research-ledger-input-v1';

            SELECT count(*) INTO invalid_lineage_capability_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            WHERE (
                SELECT COALESCE(
                    jsonb_agg(to_jsonb(ref_item->>'capability')
                        ORDER BY ref_item->>'capability'),
                    '[]'::jsonb
                )
                FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                    AS ref(ref_item)
            ) IS DISTINCT FROM required_capabilities;

            SELECT count(*) INTO invalid_lineage_ref_count
            FROM (
                SELECT lineage_item->>'sample_id' AS sample_id,
                       jsonb_build_array(
                           ref_item->>'capability',
                           ref_item->>'snapshot_id',
                           ref_item->>'normalized_observation_id'
                       ) AS ref_key
                FROM jsonb_array_elements(report_row.sample_lineage)
                    AS lineage(lineage_item)
                CROSS JOIN jsonb_array_elements(lineage_item->'source_observation_refs')
                    AS ref(ref_item)
                GROUP BY lineage_item->>'sample_id', ref_key
                HAVING count(*) <> 1
            ) AS duplicate_refs;

            SELECT invalid_lineage_ref_count + count(*)
            INTO invalid_lineage_ref_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            CROSS JOIN jsonb_array_elements(lineage_item->'source_observation_refs')
                AS ref(ref_item)
            LEFT JOIN LATERAL (
                SELECT source_item
                FROM jsonb_array_elements(report_row.source_observations)
                    AS source(source_item)
                WHERE source_item#>>'{key,capability}' = ref_item->>'capability'
                  AND source_item#>>'{normalized_observation,snapshot_id}' =
                        ref_item->>'snapshot_id'
                  AND source_item#>>'{key,normalized_observation_id}' =
                        ref_item->>'normalized_observation_id'
            ) AS resolved ON TRUE
            WHERE resolved.source_item IS NULL
               OR ref_item->>'snapshot_sha256' IS DISTINCT FROM
                    resolved.source_item#>>'{normalized_observation,snapshot_sha256}'
               OR ref_item->>'raw_observation_id' IS DISTINCT FROM
                    resolved.source_item#>>'{normalized_observation,raw_observation_id}'
               OR ref_item->>'observation_revision_id' IS DISTINCT FROM
                    resolved.source_item#>>'{normalized_observation,observation_revision_id}'
               OR ref_item->>'raw_payload_sha256' IS DISTINCT FROM
                    resolved.source_item#>>'{normalized_observation,raw_payload_sha256}'
               OR ref_item->>'normalized_content_sha256' IS DISTINCT FROM
                    resolved.source_item#>>'{normalized_observation,normalized_content_sha256}'
               OR (resolved.source_item#>>'{normalized_observation,event_time}')::timestamptz
                     > (lineage_item->>'decision_time_utc')::timestamptz
               OR (resolved.source_item#>>'{normalized_observation,available_at}')::timestamptz
                     > (lineage_item->>'decision_time_utc')::timestamptz
               OR (resolved.source_item#>>'{normalized_observation,event_time}')::timestamptz
                     > (lineage_item->>'feature_available_at_utc')::timestamptz
               OR (resolved.source_item#>>'{normalized_observation,available_at}')::timestamptz
                     > (lineage_item->>'feature_available_at_utc')::timestamptz
               OR (resolved.source_item#>>'{normalized_observation,valid_from}')::timestamptz
                    > (lineage_item->>'decision_time_utc')::timestamptz
               OR (
                    resolved.source_item#>>'{normalized_observation,valid_to}' IS NOT NULL
                    AND (lineage_item->>'decision_time_utc')::timestamptz >=
                        (resolved.source_item#>>'{normalized_observation,valid_to}')::timestamptz
               );

            SELECT count(*) INTO unused_source_count
            FROM jsonb_array_elements(report_row.source_observations)
                AS source(source_item)
            WHERE NOT EXISTS (
                SELECT 1
                FROM jsonb_array_elements(report_row.sample_lineage)
                    AS lineage(lineage_item)
                CROSS JOIN jsonb_array_elements(lineage_item->'source_observation_refs')
                    AS ref(ref_item)
                WHERE ref_item->>'capability' = source_item#>>'{key,capability}'
                  AND ref_item->>'snapshot_id' =
                        source_item#>>'{normalized_observation,snapshot_id}'
                  AND ref_item->>'normalized_observation_id' =
                        source_item#>>'{key,normalized_observation_id}'
            );

            SELECT count(*) INTO invalid_derivation_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            LEFT JOIN LATERAL (
                SELECT source_item
                FROM jsonb_array_elements(report_row.source_observations)
                    AS source(source_item)
                WHERE source_item#>>'{key,capability}' =
                        lineage_item#>>'{feature_derivation,source_observation_key,capability}'
                  AND source_item#>>'{key,normalized_observation_id}' =
                        lineage_item#>>'{feature_derivation,source_observation_key,normalized_observation_id}'
            ) AS resolved ON TRUE
            WHERE resolved.source_item IS NULL
               OR lineage_item#>>'{feature_derivation,schema_version}'
                    IS DISTINCT FROM 'phase5-source-feature-derivation-v1'
               OR lineage_item#>>'{feature_derivation,formula_id}'
                    IS DISTINCT FROM 'source-decimal-times-frozen-multiplier-v1'
               OR lineage_item#>>'{feature_derivation,source_payload_field}'
                    NOT IN ('open','volume')
               OR lineage_item#>>'{feature_derivation,derivation_sha256}'
                    !~ '^[0-9a-f]{64}$'
               OR NOT EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                        AS ref(ref_item)
                    WHERE ref_item->>'capability' =
                            lineage_item#>>'{feature_derivation,source_observation_key,capability}'
                      AND ref_item->>'normalized_observation_id' =
                            lineage_item#>>'{feature_derivation,source_observation_key,normalized_observation_id}'
               )
               OR (
                    resolved.source_item#>'{normalized_observation,payload}'
                        ->> (lineage_item#>>'{feature_derivation,source_payload_field}')
                  )::numeric
                    * (lineage_item#>>'{feature_derivation,multiplier}')::numeric
                    IS DISTINCT FROM
                        (lineage_item#>>'{feature_derivation,derived_feature_value}')::numeric;

            SELECT count(*) INTO invalid_membership_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            LEFT JOIN LATERAL (
                SELECT source_item
                FROM jsonb_array_elements(report_row.source_observations)
                    AS source(source_item)
                WHERE source_item#>>'{key,capability}' = 'universe_membership'
                  AND source_item#>>'{key,capability}' =
                        lineage_item#>>'{membership_source_observation_key,capability}'
                  AND source_item#>>'{key,normalized_observation_id}' =
                        lineage_item#>>'{membership_source_observation_key,normalized_observation_id}'
            ) AS membership_source ON TRUE
            LEFT JOIN LATERAL (
                SELECT source_item
                FROM jsonb_array_elements(report_row.source_observations)
                    AS source(source_item)
                WHERE source_item#>>'{key,capability}' =
                        lineage_item#>>'{feature_derivation,source_observation_key,capability}'
                  AND source_item#>>'{key,normalized_observation_id}' =
                        lineage_item#>>'{feature_derivation,source_observation_key,normalized_observation_id}'
            ) AS feature_source ON TRUE
            WHERE membership_source.source_item IS NULL
               OR feature_source.source_item IS NULL
               OR membership_source.source_item->>'disposition'
                    NOT IN ('included_as_of','retained_historical_vintage')
               OR membership_source.source_item#>>'{normalized_observation,payload,record_type}'
                    IS DISTINCT FROM 'universe_membership'
               OR membership_source.source_item#>>'{normalized_observation,payload,status}'
                    IS DISTINCT FROM 'included'
               OR (
                    membership_source.source_item
                        #>>'{normalized_observation,available_at}'
                  )::timestamptz
                    > (lineage_item->>'decision_time_utc')::timestamptz
               OR (
                    membership_source.source_item
                        #>>'{normalized_observation,valid_from}'
                  )::timestamptz
                    > (lineage_item->>'decision_time_utc')::timestamptz
               OR (
                    membership_source.source_item#>>'{normalized_observation,valid_to}'
                        IS NOT NULL
                    AND (lineage_item->>'decision_time_utc')::timestamptz >=
                        (membership_source.source_item#>>'{normalized_observation,valid_to}')::timestamptz
               )
               OR membership_source.source_item#>>'{normalized_observation,instrument_id}'
                    IS DISTINCT FROM
                        feature_source.source_item#>>'{normalized_observation,instrument_id}'
               OR membership_source.source_item#>>'{normalized_observation,listing_id}'
                    IS DISTINCT FROM
                        feature_source.source_item#>>'{normalized_observation,listing_id}'
               OR NOT EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                        AS ref(ref_item)
                    WHERE ref_item->>'capability' = 'universe_membership'
                      AND ref_item->>'normalized_observation_id' =
                            lineage_item#>>'{membership_source_observation_key,normalized_observation_id}'
               );

            IF invalid_lineage_count <> 0
               OR invalid_lineage_ref_count <> 0
               OR invalid_lineage_capability_count <> 0
               OR unused_source_count <> 0
               OR invalid_derivation_count <> 0
               OR invalid_membership_count <> 0 THEN
                RAISE EXCEPTION
                    'Phase 5 sample lineage contains unknown, unused, or invalid source evidence';
            END IF;

            SELECT count(*) INTO invalid_oos_lineage_count
            FROM evaluation_oos_ledger AS oos
            LEFT JOIN LATERAL (
                SELECT lineage_item
                FROM jsonb_array_elements(report_row.sample_lineage)
                    AS lineage(lineage_item)
                WHERE lineage_item->>'sample_id' = oos.sample_id
            ) AS lineage ON TRUE
            WHERE oos.report_id = checked_report_id
              AND (
                  lineage.lineage_item IS NULL
                  OR oos.sample_sha256 IS DISTINCT FROM
                        lineage.lineage_item->>'sample_sha256'
                  OR oos.decision_time_utc IS DISTINCT FROM
                        (lineage.lineage_item->>'decision_time_utc')::timestamptz
                  OR oos.source_observation_refs IS DISTINCT FROM
                        lineage.lineage_item->'source_observation_refs'
              );
            IF invalid_oos_lineage_count <> 0 THEN
                RAISE EXCEPTION 'Phase 5 OOS row differs from frozen sample lineage';
            END IF;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase5_report_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_report_id uuid;
            report evaluation_reports%ROWTYPE;
            policy evaluation_policies%ROWTYPE;
            mapping_family text;
            mapping_verdict text;
            valid_snapshot_count integer;
            actual_bundle jsonb;
            actual_bundle_hash text;
            actual_capabilities jsonb;
            actual_trial_count integer;
            actual_gate_codes text[];
            invalid_trial_oos_return_count integer;
            invalid_oos_cost_return_count integer;
            invalid_cost_group_count integer;
            invalid_stress_count integer;
            invalid_liquidity_stress_count integer;
            nonpositive_stressed_count integer;
            failing_gate_count integer;
            blocked_gate_count integer;
            nonpassing_gate_count integer;
            regime_gate_outcome text;
            derived_decision_time timestamptz;
            actual_trials jsonb;
            actual_folds jsonb;
            actual_preprocessing_fits jsonb;
            actual_oos_ledger jsonb;
            actual_cost_ledger jsonb;
            actual_gate_results jsonb;
            actual_provider_versions jsonb;
        BEGIN
            checked_report_id := NEW.report_id;
            SELECT * INTO report FROM evaluation_reports
            WHERE report_id = checked_report_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 5 report completeness target is missing';
            END IF;

            SELECT * INTO policy FROM evaluation_policies
            WHERE policy_id = report.policy_id
              AND policy_version = report.policy_version;
            IF NOT FOUND OR policy.policy_sha256 IS DISTINCT FROM report.policy_sha256 THEN
                RAISE EXCEPTION 'Phase 5 report frozen policy hash mismatch';
            END IF;
            PERFORM validate_phase5_report_source_lineage(checked_report_id);

            SELECT canonical_family, research_verdict
            INTO mapping_family, mapping_verdict
            FROM research_mapping_versions
            WHERE id = report.mapping_id;
            IF NOT FOUND OR mapping_verdict <> 'BUILD_RESEARCH'
               OR mapping_family NOT IN (
                    'A_CROSS_SECTIONAL_EQUITY_RANKING',
                    'B_TIME_SERIES_MOMENTUM_REGIME',
                    'C_OFFICIAL_EVENT_TEXT_OVERLAY'
               ) THEN
                RAISE EXCEPTION 'Phase 5 report mapping is not authorized BUILD_RESEARCH';
            END IF;
            IF mapping_family IS DISTINCT FROM policy.strategy_family
               OR report.mapping_version IS DISTINCT FROM (
                    SELECT version_number FROM research_mapping_versions
                    WHERE id = report.mapping_id
               )
               OR report.mapping_input_sha256 IS DISTINCT FROM (
                    SELECT mapping_input_sha256 FROM research_mapping_versions
                    WHERE id = report.mapping_id
               ) THEN
                RAISE EXCEPTION 'Phase 5 report mapping lineage is not frozen exactly';
            END IF;

            IF NOT phase5_exact_ordinals(
                    'evaluation_report_snapshots'::regclass,
                    'report_id', checked_report_id, report.expected_snapshot_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_trials'::regclass,
                    'report_id', checked_report_id, report.expected_trial_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_folds'::regclass,
                    'report_id', checked_report_id, report.expected_fold_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_preprocessing_fits'::regclass,
                    'report_id', checked_report_id,
                    report.expected_preprocessing_fit_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_oos_ledger'::regclass,
                    'report_id', checked_report_id, report.expected_oos_ledger_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_cost_ledger'::regclass,
                    'report_id', checked_report_id, report.expected_cost_ledger_count)
               OR NOT phase5_exact_ordinals(
                    'evaluation_gate_results'::regclass,
                    'report_id', checked_report_id, report.expected_gate_result_count) THEN
                RAISE EXCEPTION 'Phase 5 report has incomplete exact child counts';
            END IF;

            SELECT COALESCE(
                jsonb_agg(
                    payload || jsonb_build_object(
                        'trial_id', trial_id::text,
                        'trial_sha256', trial_sha256
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_trials
            FROM evaluation_trials WHERE report_id = checked_report_id;
            SELECT COALESCE(
                jsonb_agg(
                    payload || jsonb_build_object(
                        'fold_id', fold_id::text,
                        'fold_sha256', fold_sha256
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_folds
            FROM evaluation_folds WHERE report_id = checked_report_id;
            SELECT COALESCE(
                jsonb_agg(record_payload ORDER BY ordinal),
                '[]'::jsonb
            ) INTO actual_preprocessing_fits
            FROM evaluation_preprocessing_fits WHERE report_id = checked_report_id;
            SELECT COALESCE(
                jsonb_agg(
                    payload || jsonb_build_object(
                        'ledger_entry_id', oos_entry_id::text,
                        'ledger_entry_sha256', oos_entry_sha256
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_oos_ledger
            FROM evaluation_oos_ledger WHERE report_id = checked_report_id;
            SELECT COALESCE(
                jsonb_agg(
                    payload || jsonb_build_object(
                        'cost_entry_id', cost_entry_id::text,
                        'cost_entry_sha256', cost_entry_sha256
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_cost_ledger
            FROM evaluation_cost_ledger WHERE report_id = checked_report_id;
            SELECT COALESCE(
                jsonb_agg(
                    payload || jsonb_build_object(
                        'gate_result_id', gate_result_id::text,
                        'gate_result_sha256', gate_result_sha256
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_gate_results
            FROM evaluation_gate_results WHERE report_id = checked_report_id;

            IF report.payload->'trials' IS DISTINCT FROM actual_trials
               OR report.payload->'folds' IS DISTINCT FROM actual_folds
               OR report.payload->'preprocessing_fits'
                    IS DISTINCT FROM actual_preprocessing_fits
               OR report.payload->'oos_ledger' IS DISTINCT FROM actual_oos_ledger
               OR report.payload->'cost_ledger' IS DISTINCT FROM actual_cost_ledger
               OR report.payload->'gates' IS DISTINCT FROM actual_gate_results THEN
                RAISE EXCEPTION 'Phase 5 report payload differs from persisted child artifacts';
            END IF;

            SELECT count(*) INTO actual_trial_count
            FROM evaluation_trials WHERE report_id = checked_report_id;
            IF actual_trial_count <> report.raw_trial_count THEN
                RAISE EXCEPTION 'Phase 5 raw trial count omits failed or abandoned trials';
            END IF;
            SELECT max(decision_time_utc) INTO derived_decision_time
            FROM evaluation_oos_ledger WHERE report_id = checked_report_id;
            IF report.expected_oos_ledger_count > 0
               AND report.decision_time_utc IS DISTINCT FROM derived_decision_time THEN
                RAISE EXCEPTION 'Phase 5 report decision time is not derived from OOS evidence';
            END IF;

            SELECT count(*) INTO valid_snapshot_count
            FROM evaluation_report_snapshots AS binding
            JOIN data_snapshots AS snapshot
              ON snapshot.snapshot_id = binding.snapshot_id
             AND snapshot.snapshot_sha256 = binding.snapshot_sha256
            JOIN data_snapshot_manifests AS manifest
              ON manifest.snapshot_id = snapshot.snapshot_id
             AND manifest.snapshot_sha256 = snapshot.snapshot_sha256
            WHERE binding.report_id = checked_report_id
              AND snapshot.mapping_id = report.mapping_id
              AND snapshot.synthetic
              AND snapshot.quality_status IN (
                  'data_quality_accepted',
                  'data_quality_accepted_with_warnings'
              )
              AND snapshot.capability = binding.capability
              AND snapshot.provider_id = binding.provider_id
              AND snapshot.adapter_id = binding.adapter_id
              AND snapshot.adapter_version = binding.adapter_version
              AND snapshot.dataset_id = binding.dataset_id
              AND snapshot.product_id = binding.product_id
              AND snapshot.fixture_set_version = binding.fixture_set_version;
            IF valid_snapshot_count <> report.expected_snapshot_count THEN
                RAISE EXCEPTION 'Phase 5 report has invalid synthetic snapshot lineage';
            END IF;

            SELECT COALESCE(
                jsonb_agg(payload->'snapshot_evidence' ORDER BY ordinal),
                '[]'::jsonb
            ) INTO actual_bundle
            FROM evaluation_report_snapshots
            WHERE report_id = checked_report_id;
            IF report.snapshot_bundle_canonical_json::jsonb IS DISTINCT FROM actual_bundle THEN
                RAISE EXCEPTION 'Phase 5 snapshot bundle canonical payload mismatch';
            END IF;
            IF report.payload->'data_snapshots' IS DISTINCT FROM actual_bundle THEN
                RAISE EXCEPTION 'Phase 5 report payload snapshot evidence mismatch';
            END IF;
            SELECT COALESCE(
                jsonb_agg(
                    to_jsonb(provider_id || ':' || adapter_version || ':' || capability)
                    ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO actual_provider_versions
            FROM evaluation_report_snapshots WHERE report_id = checked_report_id;
            IF report.payload->'provider_source_versions'
                    IS DISTINCT FROM actual_provider_versions THEN
                RAISE EXCEPTION 'Phase 5 report provider versions mismatch';
            END IF;
            actual_bundle_hash := encode(
                sha256(
                    convert_to('phase5-snapshot-bundle-v1', 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(report.snapshot_bundle_canonical_json, 'UTF8')
                ),
                'hex'
            );
            IF report.snapshot_bundle_sha256 IS DISTINCT FROM actual_bundle_hash THEN
                RAISE EXCEPTION 'Phase 5 snapshot bundle hash mismatch';
            END IF;

            SELECT COALESCE(
                jsonb_agg(to_jsonb(capability) ORDER BY ordinal),
                '[]'::jsonb
            ) INTO actual_capabilities
            FROM evaluation_report_snapshots WHERE report_id = checked_report_id;
            IF actual_capabilities IS DISTINCT FROM policy.required_snapshot_capabilities THEN
                RAISE EXCEPTION 'Phase 5 report lacks required snapshot capabilities';
            END IF;

            SELECT count(*) INTO invalid_trial_oos_return_count
            FROM evaluation_oos_ledger AS oos
            JOIN evaluation_trials AS trial
              ON trial.report_id = oos.report_id
             AND trial.trial_id = oos.trial_id
            WHERE oos.report_id = checked_report_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(trial.return_timestamps_utc)
                      WITH ORDINALITY AS timestamp_item(value, ordinal)
                  JOIN jsonb_array_elements_text(trial.return_statuses)
                      WITH ORDINALITY AS status_item(value, ordinal) USING (ordinal)
                  JOIN jsonb_array_elements(trial.net_returns)
                      WITH ORDINALITY AS return_item(value, ordinal) USING (ordinal)
                  WHERE timestamp_item.value::timestamptz = oos.decision_time_utc
                    AND status_item.value = oos.return_status
                    AND (
                        (return_item.value = 'null'::jsonb
                         AND oos.baseline_net_return IS NULL)
                        OR (
                            return_item.value <> 'null'::jsonb
                            AND (return_item.value #>> '{}')::numeric
                                IS NOT DISTINCT FROM oos.baseline_net_return
                        )
                    )
              );

            SELECT count(*) INTO invalid_oos_cost_return_count
            FROM evaluation_cost_ledger AS cost
            LEFT JOIN evaluation_oos_ledger AS oos
              ON oos.report_id = cost.report_id
             AND oos.sample_id = cost.sample_id
            WHERE cost.report_id = checked_report_id
              AND (
                  oos.oos_entry_id IS NULL
                  OR cost.return_status IS DISTINCT FROM oos.return_status
                  OR (
                      cost.scenario = 'baseline'
                      AND (
                          cost.net_return IS DISTINCT FROM oos.baseline_net_return
                          OR (
                              cost.fill_status = 'filled'
                              AND cost.gross_return IS DISTINCT FROM oos.gross_return
                          )
                      )
                  )
              );
            IF invalid_trial_oos_return_count <> 0
               OR invalid_oos_cost_return_count <> 0 THEN
                RAISE EXCEPTION
                    'Phase 5 trial, OOS, and cost return statuses are not reconciled';
            END IF;

            SELECT array_agg(gate_code ORDER BY gate_code),
                   count(*) FILTER (WHERE outcome = 'fail'),
                   count(*) FILTER (
                       WHERE outcome IN ('blocked_missing_policy','blocked_uncomputable')
                   ),
                   count(*) FILTER (WHERE outcome <> 'pass'),
                   max(outcome) FILTER (WHERE gate_code = 'REGIME')
            INTO actual_gate_codes, failing_gate_count, blocked_gate_count,
                 nonpassing_gate_count, regime_gate_outcome
            FROM evaluation_gate_results WHERE report_id = checked_report_id;
            IF actual_gate_codes IS DISTINCT FROM ARRAY[
                'COST_STRESS','CV_CHRONOLOGY','DATA_PIT','DSR','LEAKAGE','PBO',
                'PREPROCESSING','REGIME','REPRODUCIBILITY','RISK_LIMITS',
                'SAMPLE_ADEQUACY','TRIAL_REGISTRY'
            ]::text[] THEN
                RAISE EXCEPTION 'Phase 5 report does not contain the exact gate set';
            END IF;

            SELECT count(*) INTO invalid_cost_group_count
            FROM (
                SELECT oos.sample_id
                FROM evaluation_oos_ledger AS oos
                LEFT JOIN evaluation_cost_ledger AS cost
                  ON cost.report_id = oos.report_id
                 AND cost.sample_id = oos.sample_id
                WHERE oos.report_id = checked_report_id
                GROUP BY oos.sample_id
                HAVING count(cost.cost_entry_id) <> 3
                    OR count(DISTINCT cost.scenario) <> 3
                    OR count(DISTINCT cost.allocation_input_sha256) <> 1
            ) AS invalid_groups;
            SELECT count(*) INTO invalid_stress_count
            FROM evaluation_cost_ledger AS baseline
            JOIN evaluation_cost_ledger AS stressed
              ON stressed.report_id = baseline.report_id
             AND stressed.sample_id = baseline.sample_id
             AND stressed.scenario = 'all_cost_stress'
            WHERE baseline.report_id = checked_report_id
              AND baseline.scenario = 'baseline'
              AND (
                  stressed.fee_cost + power(10::numeric, -29) < baseline.fee_cost * 2
                  OR stressed.spread_cost + power(10::numeric, -29)
                        < baseline.spread_cost * 2
                  OR stressed.impact_cost + power(10::numeric, -29)
                        < baseline.impact_cost * 2
                  OR stressed.latency_cost + power(10::numeric, -29)
                        < baseline.latency_cost * 2
                  OR stressed.borrow_cost + power(10::numeric, -29)
                        < baseline.borrow_cost * 2
                  OR stressed.capacity_cost + power(10::numeric, -29)
                        < baseline.capacity_cost * 2
              );
            SELECT count(*) INTO nonpositive_stressed_count
            FROM (
                SELECT scenario
                FROM evaluation_cost_ledger
                WHERE report_id = checked_report_id
                  AND scenario IN ('all_cost_stress','liquidity_stress')
                GROUP BY scenario
                HAVING sum(net_return) <= 0
            ) AS nonpositive_stressed_edges;
            SELECT count(*) INTO invalid_liquidity_stress_count
            FROM evaluation_cost_ledger AS baseline
            JOIN evaluation_cost_ledger AS stressed
              ON stressed.report_id = baseline.report_id
             AND stressed.sample_id = baseline.sample_id
             AND stressed.scenario = 'liquidity_stress'
            WHERE baseline.report_id = checked_report_id
              AND baseline.scenario = 'baseline'
              AND (
                  (
                      stressed.fill_status = 'filled'
                      AND (
                          stressed.fee_cost <> baseline.fee_cost
                          OR stressed.spread_cost < baseline.spread_cost
                          OR stressed.impact_cost < baseline.impact_cost
                          OR stressed.latency_cost < baseline.latency_cost
                          OR stressed.borrow_cost < baseline.borrow_cost
                          OR stressed.participation_rate < baseline.participation_rate
                          OR (
                              stressed.spread_cost = baseline.spread_cost
                              AND stressed.impact_cost = baseline.impact_cost
                              AND stressed.latency_cost = baseline.latency_cost
                              AND stressed.borrow_cost = baseline.borrow_cost
                              AND stressed.participation_rate = baseline.participation_rate
                          )
                      )
                  )
                  OR (
                      stressed.fill_status = 'capacity_rejected'
                      AND stressed.participation_rate <= baseline.participation_rate
                  )
              );
            IF invalid_cost_group_count <> 0
               OR invalid_stress_count <> 0
               OR invalid_liquidity_stress_count <> 0 THEN
                RAISE EXCEPTION 'Phase 5 cost scenarios do not preserve exposure or 2x stress';
            END IF;

            IF report.state = 'PASS_RESEARCH'
               AND (nonpassing_gate_count <> 0 OR nonpositive_stressed_count <> 0) THEN
                RAISE EXCEPTION 'Phase 5 PASS_RESEARCH cannot bypass a gate or stressed edge';
            ELSIF report.state = 'FAIL_REJECT'
                  AND failing_gate_count = 0
                  AND nonpositive_stressed_count = 0 THEN
                RAISE EXCEPTION 'Phase 5 FAIL_REJECT requires failed evidence';
            ELSIF report.state IN ('BLOCKED_MISSING_POLICY','BLOCKED_UNCOMPUTABLE')
                  AND blocked_gate_count = 0 THEN
                RAISE EXCEPTION 'Phase 5 blocked state requires a blocked gate';
            ELSIF report.state = 'RESEARCH_ONLY_REGIME_DEPENDENT'
                  AND regime_gate_outcome NOT IN ('research_only','fail') THEN
                RAISE EXCEPTION 'Phase 5 regime-dependent state requires regime evidence';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER evaluation_reports_complete
        AFTER INSERT ON evaluation_reports
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase5_report_completeness()
        """
    )
    for table in PHASE5_REPORT_CHILD_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_report_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase5_report_completeness()
            """
        )

    op.execute(
        """
        CREATE FUNCTION reject_phase5_evaluation_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 5 evaluation records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE5_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase5_evaluation_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase5_evaluation_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE5_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")

    for table in reversed(PHASE5_REPORT_CHILD_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_report_complete ON {table}")
    op.execute("DROP TRIGGER IF EXISTS evaluation_reports_complete ON evaluation_reports")
    for table in reversed(PHASE5_POLICY_CHILD_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_policy_complete ON {table}")
    op.execute("DROP TRIGGER IF EXISTS evaluation_policies_complete ON evaluation_policies")

    op.execute(
        "DROP TRIGGER IF EXISTS evaluation_blocked_outcomes_10_payload "
        "ON evaluation_blocked_outcomes"
    )

    op.execute(
        "DROP TRIGGER IF EXISTS evaluation_report_snapshots_10_lineage "
        "ON evaluation_report_snapshots"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS evaluation_preprocessing_fits_10_record "
        "ON evaluation_preprocessing_fits"
    )
    op.execute("DROP TRIGGER IF EXISTS evaluation_trials_07_return_calendar ON evaluation_trials")
    for table in reversed(
        (
            "evaluation_trials",
            "evaluation_folds",
            "evaluation_oos_ledger",
            "evaluation_cost_ledger",
            "evaluation_gate_results",
        )
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_10_payload_columns ON {table}")
    for table in reversed((*PHASE5_POLICY_CHILD_TABLES, *PHASE5_REPORT_CHILD_TABLES)):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_00_expected_count ON {table}")
    op.execute("DROP TRIGGER IF EXISTS evaluation_reports_10_header ON evaluation_reports")
    op.execute("DROP TRIGGER IF EXISTS evaluation_policies_10_definition ON evaluation_policies")
    for table in reversed(PHASE5_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_05_identity ON {table}")

    op.execute("DROP FUNCTION IF EXISTS reject_phase5_evaluation_mutation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_blocked_outcome()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_report_completeness()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_report_source_lineage(uuid)")
    op.execute("DROP FUNCTION IF EXISTS phase5_json_payload_equivalent(jsonb, jsonb)")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_policy_completeness()")
    op.execute(
        "DROP FUNCTION IF EXISTS phase5_exact_policy_ordinals(regclass, uuid, integer, integer)"
    )
    op.execute("DROP FUNCTION IF EXISTS phase5_exact_ordinals(regclass, text, uuid, integer)")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_child_payload_columns()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_trial_return_calendar()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_preprocessing_fit_record()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_report_snapshot()")
    op.execute("DROP FUNCTION IF EXISTS guard_phase5_expected_child_count()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_report_header()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_policy_definition()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase5_artifact_identity()")

    op.drop_table("evaluation_gate_results")
    op.drop_table("evaluation_cost_ledger")
    op.drop_table("evaluation_oos_ledger")
    op.drop_table("evaluation_preprocessing_fits")
    op.drop_table("evaluation_folds")
    op.drop_table("evaluation_trials")
    op.drop_table("evaluation_report_snapshots")
    op.drop_index(
        "ix_eval_blocked_outcomes_created",
        table_name="evaluation_blocked_outcomes",
        if_exists=True,
    )
    op.drop_table("evaluation_blocked_outcomes", if_exists=True)
    op.drop_index("ix_eval_reports_policy_created", table_name="evaluation_reports")
    op.drop_index("ix_eval_reports_mapping_created", table_name="evaluation_reports")
    op.drop_table("evaluation_reports")
    op.drop_table("evaluation_label_specs")
    op.drop_table("evaluation_feature_specs")
    op.drop_table("evaluation_policies")
