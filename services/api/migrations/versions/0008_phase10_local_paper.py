"""Add immutable deterministic local paper-simulation artifacts.

Revision ID: 0008_phase10
Revises: 0007_phase7

The revision adds no broker, network route, credential, external submission, or
live capability.  All rows are synthetic local simulation evidence.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_phase10"
down_revision: str | None = "0007_phase7"
branch_labels: str | None = None
depends_on: str | None = None

PHASE10_TABLES = (
    "paper_simulation_runs",
    "paper_simulation_checks",
    "paper_simulation_ledger_entries",
)

AUTHORITY_LOCK_TABLES = (
    "approval_policies",
    "approval_scopes",
    "approval_authorizations",
)

PHASE10_CHECK_CODES = (
    "SOURCE_APPROVAL_EXACT",
    "TRANSITION_APPROVAL_FRESH",
    "RESEARCH_PREREQUISITES_COMPLETE",
    "SIMULATION_CONFIGURATION_EXACT",
    "RISK_CONTEXT_EXACT",
    "COST_SLIPPAGE_COMPLETE",
    "LOCAL_BOUNDARY_ENFORCED",
)

PHASE10_APPEND_ONLY_ERROR = "Phase 10 local paper simulation artifacts are append-only"


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _payload() -> sa.Column[object]:
    return sa.Column(
        "payload",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )


def _decimal(column_name: str, *, nullable: bool = False) -> sa.Column[object]:
    return sa.Column(
        column_name,
        sa.Numeric(precision=38, scale=18),
        nullable=nullable,
    )


def _hash_check(columns: Iterable[str], *, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        " AND ".join(f"{column} ~ '^[0-9a-f]{{64}}$'" for column in columns),
        name=name,
    )


def _check_codes_sql() -> str:
    return ",".join(f"'{code}'" for code in PHASE10_CHECK_CODES)


def _check_registry_json_sql() -> str:
    return "'[" + ",".join(f'"{code}"' for code in PHASE10_CHECK_CODES) + "]'::jsonb"


def upgrade() -> None:
    op.create_table(
        "paper_simulation_runs",
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("currentness_state_sha256", sa.String(length=64), nullable=False),
        sa.Column("simulation_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_assessment_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("transition_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transition_assessment_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("transition_currentness_state_sha256", sa.String(length=64), nullable=False),
        sa.Column("transition_revocation_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("revalidation_proof_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revalidation_proof_sha256", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("phase6_lineage_sha256", sa.String(length=64), nullable=False),
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
        sa.Column("configuration_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("configuration_id", sa.String(length=256), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("phase10_code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("raw_trial_count", sa.Integer(), nullable=False),
        _decimal("effective_trial_count"),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("simulated_paper_only", sa.Boolean(), nullable=False),
        sa.Column("local_mock_only", sa.Boolean(), nullable=False),
        sa.Column("external_submission", sa.Boolean(), nullable=False),
        sa.Column("external_routing_absent", sa.Boolean(), nullable=False),
        sa.Column("live_path_absent", sa.Boolean(), nullable=False),
        sa.Column("no_personalized_investment_advice", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claimed", sa.Boolean(), nullable=False),
        sa.Column(
            "artifact_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        _created_at(),
        _hash_check(
            (
                "artifact_sha256",
                "request_fingerprint_sha256",
                "currentness_state_sha256",
                "source_assessment_artifact_sha256",
                "transition_assessment_artifact_sha256",
                "transition_currentness_state_sha256",
                "transition_revocation_set_sha256",
                "revalidation_proof_sha256",
                "research_artifact_sha256",
                "phase6_lineage_sha256",
                "approval_policy_sha256",
                "approval_scope_sha256",
                "authorization_sha256",
                "risk_input_sha256",
                "configuration_sha256",
            ),
            name="ck_paper_simulation_run_hashes",
        ),
        sa.CheckConstraint(
            "artifact_schema_version = 'phase10-local-paper-simulation-v1' "
            "AND btrim(simulation_idempotency_key) <> '' "
            "AND configuration_id = 'phase10-a-local-mock-qa-v1' "
            "AND outcome IN ('SIMULATED_COMPLETE','BLOCKED') "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) >= 1 "
            "AND phase10_code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND raw_trial_count >= 0 AND effective_trial_count >= 0 "
            "AND synthetic AND simulated_paper_only AND local_mock_only "
            "AND NOT external_submission AND external_routing_absent "
            "AND live_path_absent AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_paper_simulation_run_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["source_assessment_id", "source_assessment_artifact_sha256"],
            ["approval_assessments.assessment_id", "approval_assessments.artifact_sha256"],
            name="fk_paper_simulation_source_assessment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transition_assessment_id", "transition_assessment_artifact_sha256"],
            ["approval_assessments.assessment_id", "approval_assessments.artifact_sha256"],
            name="fk_paper_simulation_transition_assessment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id", "research_artifact_sha256"],
            ["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"],
            name="fk_paper_simulation_research_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_policy_version_id", "approval_policy_sha256"],
            ["approval_policies.approval_policy_version_id", "approval_policies.policy_sha256"],
            name="fk_paper_simulation_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_scope_version_id", "approval_scope_sha256"],
            ["approval_scopes.approval_scope_version_id", "approval_scopes.scope_sha256"],
            name="fk_paper_simulation_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["human_authorization_evidence_id", "authorization_sha256"],
            [
                "approval_authorizations.human_authorization_evidence_id",
                "approval_authorizations.authorization_sha256",
            ],
            name="fk_paper_simulation_authorization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["risk_input_id", "risk_input_sha256"],
            ["approval_risk_inputs.risk_input_id", "approval_risk_inputs.risk_input_sha256"],
            name="fk_paper_simulation_risk_input",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("simulation_run_id", name="pk_paper_simulation_runs"),
        sa.UniqueConstraint("artifact_sha256", name="uq_paper_simulation_artifact"),
        sa.UniqueConstraint("request_fingerprint_sha256", name="uq_paper_simulation_request"),
        sa.UniqueConstraint("simulation_idempotency_key", name="uq_paper_simulation_idempotency"),
        sa.UniqueConstraint("revalidation_proof_id", name="uq_paper_simulation_revalidation_id"),
        sa.UniqueConstraint(
            "revalidation_proof_sha256", name="uq_paper_simulation_revalidation_hash"
        ),
        sa.UniqueConstraint(
            "simulation_run_id",
            "artifact_sha256",
            name="uq_paper_simulation_run_artifact",
        ),
    )
    op.create_index(
        "ix_paper_simulation_source_created",
        "paper_simulation_runs",
        ["source_assessment_id", "created_at_utc", "simulation_run_id"],
    )

    op.create_table(
        "paper_simulation_checks",
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("simulation_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
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
            ("simulation_artifact_sha256", "check_sha256"),
            name="ck_paper_simulation_check_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase10-local-simulation-check-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE10_CHECK_CODES)} "
            f"AND code IN ({_check_codes_sql()}) "
            "AND status IN ('PASS','FAIL','BLOCKED','UNCOMPUTABLE') "
            "AND btrim(reason_code) <> '' "
            "AND jsonb_typeof(evidence_sha256s) = 'array' "
            "AND jsonb_array_length(evidence_sha256s) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_paper_simulation_check_identity",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id", "simulation_artifact_sha256"],
            ["paper_simulation_runs.simulation_run_id", "paper_simulation_runs.artifact_sha256"],
            name="fk_paper_simulation_check_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "simulation_run_id",
            "ordinal",
            name="pk_paper_simulation_checks",
        ),
        sa.UniqueConstraint(
            "simulation_run_id",
            "code",
            name="uq_paper_simulation_check_code",
        ),
        sa.UniqueConstraint(
            "simulation_run_id",
            "check_sha256",
            name="uq_paper_simulation_check_hash",
        ),
    )

    op.create_table(
        "paper_simulation_ledger_entries",
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("simulation_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("ledger_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_entry_sha256", sa.String(length=64), nullable=False),
        sa.Column("mock_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mock_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("mock_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mock_observation_sha256", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=256), nullable=False),
        sa.Column("universe_id", sa.String(length=256), nullable=False),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.String(length=256), nullable=False),
        sa.Column("signal_rule_id", sa.String(length=256), nullable=False),
        _decimal("signal_value"),
        sa.Column("signal_state", sa.String(length=16), nullable=False),
        sa.Column("simulated_side", sa.String(length=16), nullable=False),
        sa.Column("fill_status", sa.String(length=32), nullable=False),
        _decimal("approved_proposed_notional"),
        _decimal("requested_quantity"),
        _decimal("filled_quantity"),
        _decimal("rejected_quantity"),
        _decimal("unfilled_quantity"),
        _decimal("reference_price"),
        _decimal("simulated_fill_price"),
        _decimal("average_daily_volume"),
        _decimal("volatility"),
        _decimal("participation_rate"),
        _decimal("commission_cost"),
        _decimal("regulatory_fee_cost"),
        _decimal("spread_cost"),
        _decimal("impact_cost"),
        _decimal("latency_cost"),
        _decimal("borrow_cost"),
        _decimal("capacity_cost"),
        _decimal("total_cost"),
        _decimal("position_quantity_before"),
        _decimal("position_quantity_after"),
        _decimal("cash_before"),
        _decimal("cash_after"),
        sa.Column("source_transaction_cost_model_id", sa.String(length=256), nullable=False),
        sa.Column("source_slippage_model_id", sa.String(length=256), nullable=False),
        sa.Column("local_cost_model_id", sa.String(length=256), nullable=False),
        sa.Column("local_slippage_model_id", sa.String(length=256), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("simulated_paper_only", sa.Boolean(), nullable=False),
        sa.Column("local_mock_only", sa.Boolean(), nullable=False),
        sa.Column("external_submission", sa.Boolean(), nullable=False),
        sa.Column("live_path_absent", sa.Boolean(), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            (
                "simulation_artifact_sha256",
                "ledger_entry_sha256",
                "mock_snapshot_sha256",
                "mock_observation_sha256",
            ),
            name="ck_paper_simulation_ledger_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase10-local-simulation-ledger-v1' "
            "AND ordinal = 1 AND entity_id = 'SYNTHETIC-ASSET-001' "
            "AND model_id = 'sector-relative-rank-linear-v1' "
            "AND signal_rule_id = 'phase6-a-score-positive-long-flat-v1' "
            "AND signal_state = 'LONG' AND simulated_side = 'BUY' "
            "AND fill_status = 'SIMULATED_FILLED' "
            "AND approved_proposed_notional > 0 "
            "AND requested_quantity > 0 AND filled_quantity > 0 "
            "AND rejected_quantity = 0 AND unfilled_quantity = 0 "
            "AND filled_quantity = requested_quantity "
            "AND reference_price > 0 AND simulated_fill_price > 0 "
            "AND average_daily_volume > 0 AND volatility >= 0 "
            "AND participation_rate > 0 AND participation_rate <= 1 "
            "AND commission_cost >= 0 AND regulatory_fee_cost >= 0 "
            "AND spread_cost >= 0 AND impact_cost >= 0 AND latency_cost >= 0 "
            "AND borrow_cost >= 0 AND capacity_cost >= 0 AND total_cost >= 0 "
            "AND position_quantity_before >= 0 AND position_quantity_after >= 0 "
            "AND cash_before >= 0 AND cash_after >= 0 "
            "AND local_cost_model_id = 'phase10-local-transparent-cost-v1' "
            "AND local_slippage_model_id = 'phase10-local-transparent-slippage-v1' "
            "AND synthetic AND simulated_paper_only AND local_mock_only "
            "AND NOT external_submission AND live_path_absent "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_paper_simulation_ledger_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id", "simulation_artifact_sha256"],
            ["paper_simulation_runs.simulation_run_id", "paper_simulation_runs.artifact_sha256"],
            name="fk_paper_simulation_ledger_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "simulation_run_id",
            "ordinal",
            name="pk_paper_simulation_ledger_entries",
        ),
        sa.UniqueConstraint("ledger_entry_id", name="uq_paper_simulation_ledger_entry"),
        sa.UniqueConstraint("ledger_entry_sha256", name="uq_paper_simulation_ledger_hash"),
    )

    _install_validation_functions()
    _install_validation_triggers()
    _install_append_only_guards()


def _install_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION own_phase10_created_at_utc()
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
        CREATE FUNCTION phase10_lock_authority_version()
        RETURNS trigger AS $$
        BEGIN
            IF TG_TABLE_NAME = 'approval_policies' THEN
                PERFORM pg_advisory_xact_lock(
                    hashtextextended('phase10-policy:' || NEW.policy_id, 0)
                );
            ELSIF TG_TABLE_NAME = 'approval_scopes' THEN
                PERFORM pg_advisory_xact_lock(
                    hashtextextended('phase10-scope:' || NEW.scope_id, 0)
                );
            ELSIF TG_TABLE_NAME = 'approval_authorizations' THEN
                PERFORM pg_advisory_xact_lock(
                    hashtextextended(NEW.human_authorization_evidence_id::text, 0)
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase10_root_payload()
        RETURNS trigger AS $$
        DECLARE
            body jsonb;
            configuration jsonb;
            revalidation_proof jsonb;
            expected_currentness text;
            expected_revalidation_proof text;
            expected_mock_snapshot text;
            expected_mock_observation text;
            expected_request text;
        BEGIN
            body := NEW.artifact_payload;
            configuration := body->'configuration';
            revalidation_proof := body->'transition_revalidation_proof';
            expected_currentness := phase6_domain_sha256(
                'phase10-local-simulation-currentness-v1',
                jsonb_build_object(
                    'source_assessment_sha256', NEW.source_assessment_artifact_sha256,
                    'transition_assessment_sha256',
                        NEW.transition_assessment_artifact_sha256,
                    'transition_currentness_state_sha256',
                        NEW.transition_currentness_state_sha256,
                    'transition_revocation_set_sha256',
                        NEW.transition_revocation_set_sha256,
                    'revalidation_proof_sha256',
                        NEW.revalidation_proof_sha256
                )
            );
            expected_revalidation_proof := phase6_domain_sha256(
                'phase10-local-simulation-revalidation-v1',
                revalidation_proof - ARRAY[
                    'revalidation_proof_id','revalidation_proof_sha256'
                ]::text[]
            );
            expected_mock_snapshot := phase6_domain_sha256(
                'phase10-local-mock-snapshot-v1',
                jsonb_build_object(
                    'configuration_id', NEW.configuration_id,
                    'research_run_id', NEW.research_run_id::text,
                    'research_artifact_sha256', NEW.research_artifact_sha256,
                    'observed_at_utc', configuration->'observed_at_utc',
                    'available_at_utc', configuration->'available_at_utc',
                    'entity_id', 'SYNTHETIC-ASSET-001',
                    'universe_id', configuration->>'mock_universe_id',
                    'reference_price', configuration->'reference_price',
                    'average_daily_volume', configuration->'average_daily_volume',
                    'volatility', configuration->'volatility',
                    'synthetic', true,
                    'local_mock_only', true
                )
            );
            expected_mock_observation := phase6_domain_sha256(
                'phase10-local-mock-observation-v1',
                jsonb_build_object(
                    'configuration_id', NEW.configuration_id,
                    'research_run_id', NEW.research_run_id::text,
                    'research_artifact_sha256', NEW.research_artifact_sha256,
                    'observed_at_utc', configuration->'observed_at_utc',
                    'available_at_utc', configuration->'available_at_utc',
                    'entity_id', 'SYNTHETIC-ASSET-001',
                    'universe_id', configuration->>'mock_universe_id',
                    'reference_price', configuration->'reference_price',
                    'average_daily_volume', configuration->'average_daily_volume',
                    'volatility', configuration->'volatility',
                    'synthetic', true,
                    'local_mock_only', true,
                    'mock_snapshot_id', configuration->'mock_snapshot_id',
                    'mock_snapshot_sha256', expected_mock_snapshot,
                    'synthetic_model_output', configuration->'synthetic_model_output'
                )
            );
            expected_request := phase6_domain_sha256(
                'phase10-local-simulation-request-v1',
                jsonb_build_object(
                    'request', jsonb_build_object(
                        'approval_assessment_id', NEW.source_assessment_id::text,
                        'simulation_idempotency_key', NEW.simulation_idempotency_key
                    ),
                    'source_assessment_sha256', NEW.source_assessment_artifact_sha256,
                    'transition_assessment_sha256',
                        NEW.transition_assessment_artifact_sha256,
                    'currentness_state_sha256', expected_currentness,
                    'revalidation_proof_sha256', expected_revalidation_proof,
                    'configuration_sha256', NEW.configuration_sha256,
                    'phase10_code_version_git_sha', NEW.phase10_code_version_git_sha
                )
            );
            IF (SELECT count(*) FROM jsonb_object_keys(body)) <> 41
               OR NOT body ?& ARRAY[
                    'artifact_schema_version','request_fingerprint_sha256',
                    'currentness_state_sha256','simulation_idempotency_key',
                    'source_assessment_id','source_assessment_artifact_sha256',
                    'transition_assessment_id','transition_assessment_artifact_sha256',
                    'transition_currentness_state_sha256',
                    'transition_revocation_set_sha256','research_run_id',
                    'transition_revalidation_proof',
                    'research_artifact_sha256','phase6_lineage_sha256',
                    'approval_policy_version_id','approval_policy_sha256',
                    'approval_scope_version_id','approval_scope_sha256',
                    'human_authorization_evidence_id','authorization_sha256',
                    'risk_input_id','risk_input_sha256','configuration','checks',
                    'ledger_entries','outcome','reason_codes',
                    'phase10_code_version_git_sha','random_seed','raw_trial_count',
                    'effective_trial_count','decision_time_utc','synthetic',
                    'simulated_paper_only','local_mock_only','external_submission',
                    'external_routing_absent','live_path_absent',
                    'no_personalized_investment_advice',
                    'no_real_performance_claimed','disclaimer'
               ]
               OR jsonb_typeof(configuration) <> 'object'
               OR jsonb_typeof(revalidation_proof) <> 'object'
               OR body->>'artifact_schema_version' IS DISTINCT FROM NEW.artifact_schema_version
               OR body->>'request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR body->>'currentness_state_sha256'
                    IS DISTINCT FROM NEW.currentness_state_sha256
               OR body->>'simulation_idempotency_key'
                    IS DISTINCT FROM NEW.simulation_idempotency_key
               OR (body->>'source_assessment_id')::uuid
                    IS DISTINCT FROM NEW.source_assessment_id
               OR body->>'source_assessment_artifact_sha256'
                    IS DISTINCT FROM NEW.source_assessment_artifact_sha256
               OR (body->>'transition_assessment_id')::uuid
                    IS DISTINCT FROM NEW.transition_assessment_id
               OR body->>'transition_assessment_artifact_sha256'
                    IS DISTINCT FROM NEW.transition_assessment_artifact_sha256
               OR body->>'transition_currentness_state_sha256'
                    IS DISTINCT FROM NEW.transition_currentness_state_sha256
               OR body->>'transition_revocation_set_sha256'
                    IS DISTINCT FROM NEW.transition_revocation_set_sha256
               OR (SELECT count(*) FROM jsonb_object_keys(revalidation_proof)) <> 12
               OR revalidation_proof->>'schema_version' IS DISTINCT FROM
                    'phase10-local-simulation-revalidation-v1'
               OR (revalidation_proof->>'revalidation_proof_id')::uuid
                    IS DISTINCT FROM NEW.revalidation_proof_id
               OR revalidation_proof->>'revalidation_proof_sha256'
                    IS DISTINCT FROM NEW.revalidation_proof_sha256
               OR revalidation_proof->>'simulation_idempotency_key'
                    IS DISTINCT FROM NEW.simulation_idempotency_key
               OR (revalidation_proof->>'source_assessment_id')::uuid
                    IS DISTINCT FROM NEW.source_assessment_id
               OR revalidation_proof->>'source_assessment_artifact_sha256'
                    IS DISTINCT FROM NEW.source_assessment_artifact_sha256
               OR (revalidation_proof->>'transition_assessment_id')::uuid
                    IS DISTINCT FROM NEW.transition_assessment_id
               OR revalidation_proof->>'transition_assessment_artifact_sha256'
                    IS DISTINCT FROM NEW.transition_assessment_artifact_sha256
               OR revalidation_proof->>'transition_currentness_state_sha256'
                    IS DISTINCT FROM NEW.transition_currentness_state_sha256
               OR revalidation_proof->>'transition_revocation_set_sha256'
                    IS DISTINCT FROM NEW.transition_revocation_set_sha256
               OR (revalidation_proof->>'decision_time_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc
               OR revalidation_proof->>'phase10_code_version_git_sha'
                    IS DISTINCT FROM NEW.phase10_code_version_git_sha
               OR expected_revalidation_proof IS DISTINCT FROM NEW.revalidation_proof_sha256
               OR phase6_uuid5(
                    'ce090e4f-afab-55ef-a6c3-ec4292ec1010'::uuid,
                    expected_revalidation_proof
                  ) IS DISTINCT FROM NEW.revalidation_proof_id
               OR (body->>'research_run_id')::uuid IS DISTINCT FROM NEW.research_run_id
               OR body->>'research_artifact_sha256'
                    IS DISTINCT FROM NEW.research_artifact_sha256
               OR body->>'phase6_lineage_sha256' IS DISTINCT FROM NEW.phase6_lineage_sha256
               OR (body->>'approval_policy_version_id')::uuid
                    IS DISTINCT FROM NEW.approval_policy_version_id
               OR body->>'approval_policy_sha256' IS DISTINCT FROM NEW.approval_policy_sha256
               OR (body->>'approval_scope_version_id')::uuid
                    IS DISTINCT FROM NEW.approval_scope_version_id
               OR body->>'approval_scope_sha256' IS DISTINCT FROM NEW.approval_scope_sha256
               OR (body->>'human_authorization_evidence_id')::uuid
                    IS DISTINCT FROM NEW.human_authorization_evidence_id
               OR body->>'authorization_sha256' IS DISTINCT FROM NEW.authorization_sha256
               OR (body->>'risk_input_id')::uuid IS DISTINCT FROM NEW.risk_input_id
               OR body->>'risk_input_sha256' IS DISTINCT FROM NEW.risk_input_sha256
               OR body->>'outcome' IS DISTINCT FROM NEW.outcome
               OR body->'reason_codes' IS DISTINCT FROM NEW.reason_codes
               OR body->>'phase10_code_version_git_sha'
                    IS DISTINCT FROM NEW.phase10_code_version_git_sha
               OR (body->>'random_seed')::bigint IS DISTINCT FROM NEW.random_seed
               OR (body->>'raw_trial_count')::integer IS DISTINCT FROM NEW.raw_trial_count
               OR (body->>'effective_trial_count')::numeric
                    IS DISTINCT FROM NEW.effective_trial_count
               OR (body->>'decision_time_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc
               OR (body->>'synthetic')::boolean IS DISTINCT FROM NEW.synthetic
               OR (body->>'simulated_paper_only')::boolean
                    IS DISTINCT FROM NEW.simulated_paper_only
               OR (body->>'local_mock_only')::boolean IS DISTINCT FROM NEW.local_mock_only
               OR (body->>'external_submission')::boolean
                    IS DISTINCT FROM NEW.external_submission
               OR (body->>'external_routing_absent')::boolean
                    IS DISTINCT FROM NEW.external_routing_absent
               OR (body->>'live_path_absent')::boolean IS DISTINCT FROM NEW.live_path_absent
               OR (body->>'no_personalized_investment_advice')::boolean
                    IS DISTINCT FROM NEW.no_personalized_investment_advice
               OR (body->>'no_real_performance_claimed')::boolean
                    IS DISTINCT FROM NEW.no_real_performance_claimed
               OR body->>'disclaimer' IS DISTINCT FROM
                    'Deterministic synthetic local paper simulation only; no external routing, '
                    'live trading, real performance claim, or personalized investment advice.'
               OR (SELECT count(*) FROM jsonb_object_keys(configuration)) <> 46
               OR configuration->>'schema_version' IS DISTINCT FROM
                    'phase10-local-simulation-configuration-v1'
               OR configuration->>'configuration_id' IS DISTINCT FROM NEW.configuration_id
               OR (configuration->>'configuration_instance_id')::uuid
                    IS DISTINCT FROM NEW.configuration_instance_id
               OR configuration->>'configuration_sha256'
                    IS DISTINCT FROM NEW.configuration_sha256
               OR (configuration->>'research_run_id')::uuid IS DISTINCT FROM NEW.research_run_id
               OR configuration->>'research_artifact_sha256'
                    IS DISTINCT FROM NEW.research_artifact_sha256
               OR (configuration->>'random_seed')::bigint IS DISTINCT FROM NEW.random_seed
               OR (configuration->>'raw_trial_count')::integer IS DISTINCT FROM NEW.raw_trial_count
               OR (configuration->>'effective_trial_count')::numeric
                    IS DISTINCT FROM NEW.effective_trial_count
               OR (configuration->>'decision_time_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc
               OR configuration->>'model_id' IS DISTINCT FROM
                    'sector-relative-rank-linear-v1'
               OR configuration->>'signal_rule_id' IS DISTINCT FROM
                    'phase6-a-score-positive-long-flat-v1'
               OR configuration->>'local_cost_model_id' IS DISTINCT FROM
                    'phase10-local-transparent-cost-v1'
               OR configuration->>'local_slippage_model_id' IS DISTINCT FROM
                    'phase10-local-transparent-slippage-v1'
               OR configuration->>'mock_entity_id' IS DISTINCT FROM
                    'SYNTHETIC-ASSET-001'
               OR configuration->>'research_configuration_id' IS DISTINCT FROM
                    'phase6-a-pass-v2'
               OR configuration->>'canonical_family' IS DISTINCT FROM
                    'A_CROSS_SECTIONAL_EQUITY_RANKING'
               OR (configuration->>'synthetic_model_output')::numeric
                    IS DISTINCT FROM 0.25::numeric
               OR (configuration->>'reference_price')::numeric
                    IS DISTINCT FROM 100::numeric
               OR (configuration->>'average_daily_volume')::numeric
                    IS DISTINCT FROM 100000::numeric
               OR (configuration->>'volatility')::numeric IS DISTINCT FROM 0.2::numeric
               OR (configuration->>'starting_cash')::numeric
                    IS DISTINCT FROM 1000000::numeric
               OR (configuration->>'synthetic')::boolean IS DISTINCT FROM TRUE
               OR (configuration->>'local_mock_only')::boolean IS DISTINCT FROM TRUE
               OR (configuration->>'external_routing_absent')::boolean
                    IS DISTINCT FROM TRUE
               OR (configuration->>'live_path_absent')::boolean IS DISTINCT FROM TRUE
               OR (configuration->>'llm_decision_role_absent')::boolean
                    IS DISTINCT FROM TRUE
               OR NOT (
                    (configuration->>'observed_at_utc')::timestamptz
                        <= (configuration->>'available_at_utc')::timestamptz
                    AND (configuration->>'available_at_utc')::timestamptz
                        <= NEW.decision_time_utc
                )
               OR (configuration->>'observed_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc - interval '2 seconds'
               OR (configuration->>'available_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc - interval '1 second'
               OR configuration->>'mock_snapshot_sha256'
                    IS DISTINCT FROM expected_mock_snapshot
               OR phase6_uuid5(
                    '2e684f7f-1de2-52fc-8639-b614b2441010'::uuid,
                    expected_mock_snapshot
                  ) IS DISTINCT FROM (configuration->>'mock_snapshot_id')::uuid
               OR configuration->>'mock_observation_sha256'
                    IS DISTINCT FROM expected_mock_observation
               OR phase6_uuid5(
                    '0d5dfb4a-bb6a-5558-a138-1c05d8581010'::uuid,
                    expected_mock_observation
                  ) IS DISTINCT FROM (configuration->>'mock_observation_id')::uuid
               OR jsonb_typeof(configuration->'source_snapshot_bindings') <> 'array'
               OR jsonb_array_length(configuration->'source_snapshot_bindings') < 1
               OR jsonb_typeof(configuration->'required_capabilities') <> 'array'
               OR jsonb_array_length(configuration->'required_capabilities') < 1
               OR jsonb_typeof(configuration->'required_audit_fields') <> 'array'
               OR jsonb_array_length(configuration->'required_audit_fields') < 10
               OR btrim(configuration->>'target_forecast_horizon') = ''
               OR (configuration->>'reference_price')::numeric <= 0
               OR (configuration->>'average_daily_volume')::numeric <= 0
               OR (configuration->>'volatility')::numeric < 0
               OR (configuration->>'starting_cash')::numeric <= 0
               OR (
                    (configuration->>'approved_proposed_notional' IS NULL)
                    IS DISTINCT FROM
                    (configuration->>'requested_quantity' IS NULL)
               )
               OR (
                    configuration->>'requested_quantity' IS NOT NULL
                    AND (configuration->>'requested_quantity')::numeric
                        * (configuration->>'reference_price')::numeric
                        IS DISTINCT FROM
                          (configuration->>'approved_proposed_notional')::numeric
               )
               OR phase6_domain_sha256(
                    'phase10-local-simulation-configuration-v1',
                    configuration - ARRAY[
                        'configuration_instance_id','configuration_sha256'
                    ]::text[]
                  ) IS DISTINCT FROM NEW.configuration_sha256
               OR phase6_uuid5(
                    '156cc8af-3b68-508b-b7f2-8bb1818f1010'::uuid,
                    NEW.configuration_sha256
                  ) IS DISTINCT FROM NEW.configuration_instance_id
               OR expected_currentness IS DISTINCT FROM NEW.currentness_state_sha256
               OR expected_request IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR phase6_uuid5(
                    '94855828-a04c-54f9-ae66-dd00ef7a1010'::uuid,
                    expected_request
                  ) IS DISTINCT FROM NEW.simulation_run_id
               OR phase6_domain_sha256(
                    'phase10-local-simulation-artifact-v1', body
                  ) IS DISTINCT FROM NEW.artifact_sha256 THEN
                RAISE EXCEPTION 'Phase 10 simulation root payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase10_current_authority()
        RETURNS trigger AS $$
        DECLARE
            source_row approval_assessments%ROWTYPE;
            transition_row approval_assessments%ROWTYPE;
            research_row research_pipeline_runs%ROWTYPE;
            source_policy_row approval_policies%ROWTYPE;
            source_scope_row approval_scopes%ROWTYPE;
            policy_row approval_policies%ROWTYPE;
            scope_row approval_scopes%ROWTYPE;
            authorization_row approval_authorizations%ROWTYPE;
            risk_row approval_risk_inputs%ROWTYPE;
            current_revocations jsonb;
            authoritative_snapshot_bindings jsonb;
            source_lineage jsonb;
            configuration jsonb;
        BEGIN
            configuration := NEW.artifact_payload->'configuration';
            PERFORM pg_advisory_xact_lock(
                hashtextextended(NEW.human_authorization_evidence_id::text, 0)
            );
            SELECT * INTO source_row FROM approval_assessments
            WHERE assessment_id = NEW.source_assessment_id
              AND artifact_sha256 = NEW.source_assessment_artifact_sha256;
            SELECT * INTO transition_row FROM approval_assessments
            WHERE assessment_id = NEW.transition_assessment_id
              AND artifact_sha256 = NEW.transition_assessment_artifact_sha256;
            SELECT * INTO research_row FROM research_pipeline_runs
            WHERE id = NEW.research_run_id
              AND artifact_sha256 = NEW.research_artifact_sha256;
            SELECT COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'ordinal', ordinal,
                        'snapshot_id', snapshot_id::text,
                        'snapshot_sha256', snapshot_sha256,
                        'binding_sha256', binding_sha256,
                        'capability', capability
                    ) ORDER BY ordinal
                ),
                '[]'::jsonb
            ) INTO authoritative_snapshot_bindings
            FROM research_snapshot_bindings
            WHERE run_id = NEW.research_run_id;
            source_lineage := source_row.artifact_payload->'phase6_lineage';
            IF source_row.assessment_id IS NULL OR transition_row.assessment_id IS NULL THEN
                RAISE EXCEPTION 'Phase 10 simulation requires exact Phase 7 assessments';
            END IF;
            SELECT * INTO source_policy_row FROM approval_policies
            WHERE approval_policy_version_id = source_row.approval_policy_version_id
              AND policy_sha256 = source_row.approval_policy_sha256;
            SELECT * INTO source_scope_row FROM approval_scopes
            WHERE approval_scope_version_id = source_row.approval_scope_version_id
              AND scope_sha256 = source_row.approval_scope_sha256;
            SELECT * INTO policy_row FROM approval_policies
            WHERE approval_policy_version_id = NEW.approval_policy_version_id
              AND policy_sha256 = NEW.approval_policy_sha256;
            SELECT * INTO scope_row FROM approval_scopes
            WHERE approval_scope_version_id = NEW.approval_scope_version_id
              AND scope_sha256 = NEW.approval_scope_sha256;
            IF source_policy_row.approval_policy_version_id IS NULL
               OR source_scope_row.approval_scope_version_id IS NULL
               OR policy_row.approval_policy_version_id IS NULL
               OR scope_row.approval_scope_version_id IS NULL THEN
                RAISE EXCEPTION 'Phase 10 simulation authority family is missing';
            END IF;
            PERFORM pg_advisory_xact_lock(
                hashtextextended('phase10-policy:' || source_policy_row.policy_id, 0)
            );
            PERFORM pg_advisory_xact_lock(
                hashtextextended('phase10-scope:' || source_scope_row.scope_id, 0)
            );
            IF research_row.id IS NULL
               OR source_row.research_run_id <> transition_row.research_run_id
               OR source_row.research_artifact_sha256
                    <> transition_row.research_artifact_sha256
               OR source_row.phase6_lineage_sha256 <> transition_row.phase6_lineage_sha256
               OR source_row.human_authorization_evidence_id
                    <> transition_row.human_authorization_evidence_id
               OR source_row.risk_input_id <> transition_row.risk_input_id
               OR transition_row.approval_policy_version_id IS DISTINCT FROM COALESCE(
                    (
                        SELECT candidate.approval_policy_version_id
                        FROM approval_policies AS candidate
                        WHERE candidate.policy_id = source_policy_row.policy_id
                          AND candidate.valid_from_utc <= NEW.decision_time_utc
                          AND NEW.decision_time_utc < candidate.expires_at_utc
                        ORDER BY candidate.policy_version DESC,
                                 candidate.approval_policy_version_id DESC
                        LIMIT 1
                    ),
                    source_row.approval_policy_version_id
               )
               OR transition_row.approval_scope_version_id IS DISTINCT FROM COALESCE(
                    (
                        SELECT candidate.approval_scope_version_id
                        FROM approval_scopes AS candidate
                        WHERE candidate.scope_id = source_scope_row.scope_id
                          AND candidate.valid_from_utc <= NEW.decision_time_utc
                          AND NEW.decision_time_utc < candidate.expires_at_utc
                        ORDER BY candidate.scope_version DESC,
                                 candidate.approval_scope_version_id DESC
                        LIMIT 1
                    ),
                    source_row.approval_scope_version_id
               )
               OR (
                    (
                        source_row.approval_policy_version_id
                            <> transition_row.approval_policy_version_id
                        OR source_row.approval_scope_version_id
                            <> transition_row.approval_scope_version_id
                    )
                    AND (
                        NEW.outcome <> 'BLOCKED'
                        OR transition_row.outcome <> 'FAIL_REJECT'
                    )
               )
               OR source_row.research_run_id <> NEW.research_run_id
               OR source_row.research_artifact_sha256 <> NEW.research_artifact_sha256
               OR source_row.phase6_lineage_sha256 <> NEW.phase6_lineage_sha256
               OR transition_row.research_run_id <> NEW.research_run_id
               OR transition_row.research_artifact_sha256 <> NEW.research_artifact_sha256
               OR transition_row.phase6_lineage_sha256 <> NEW.phase6_lineage_sha256
               OR transition_row.approval_policy_version_id
                    <> NEW.approval_policy_version_id
               OR transition_row.approval_policy_sha256 <> NEW.approval_policy_sha256
               OR transition_row.approval_scope_version_id
                    <> NEW.approval_scope_version_id
               OR transition_row.approval_scope_sha256 <> NEW.approval_scope_sha256
               OR transition_row.human_authorization_evidence_id
                    <> NEW.human_authorization_evidence_id
               OR transition_row.authorization_sha256 <> NEW.authorization_sha256
               OR transition_row.risk_input_id <> NEW.risk_input_id
               OR transition_row.risk_input_sha256 <> NEW.risk_input_sha256
               OR transition_row.currentness_state_sha256
                    <> NEW.transition_currentness_state_sha256
               OR transition_row.revocation_set_sha256
                    <> NEW.transition_revocation_set_sha256
               OR research_row.status <> 'completed'
               OR research_row.promotion_state <> 'PASS_RESEARCH'
               OR research_row.configuration_id <> 'phase6-a-pass-v2'
               OR research_row.canonical_family <>
                    'A_CROSS_SECTIONAL_EQUITY_RANKING'
               OR research_row.no_real_performance_claimed IS DISTINCT FROM TRUE
               OR research_row.paper_approval_granted IS DISTINCT FROM FALSE
               OR configuration->>'research_configuration_id'
                    IS DISTINCT FROM research_row.configuration_id
               OR configuration->>'research_configuration_sha256'
                    IS DISTINCT FROM research_row.configuration_sha256
               OR configuration->>'research_specification_sha256'
                    IS DISTINCT FROM research_row.specification_sha256
               OR configuration->>'research_snapshot_bundle_sha256'
                    IS DISTINCT FROM research_row.snapshot_bundle_sha256
               OR configuration->>'canonical_family'
                    IS DISTINCT FROM research_row.canonical_family
               OR configuration->'source_snapshot_bindings'
                    IS DISTINCT FROM authoritative_snapshot_bindings
               OR configuration->>'signal_definition_sha256' IS DISTINCT FROM
                    phase6_domain_sha256(
                        'phase10-source-signal-definition-v1',
                        research_row.artifact_payload#>'{specification,signal_definition}'
                    )
               OR configuration->>'target_forecast_horizon' IS DISTINCT FROM
                    research_row.artifact_payload#>>'{specification,target_forecast_horizon}'
               OR configuration->'required_capabilities' IS DISTINCT FROM
                    research_row.artifact_payload#>'{specification,required_capabilities}'
               OR configuration->'required_audit_fields' IS DISTINCT FROM
                    research_row.artifact_payload#>'{specification,required_audit_fields}'
               OR configuration->>'source_transaction_cost_model_id' IS DISTINCT FROM
                    research_row.artifact_payload#>>'{specification,transaction_cost_model_id}'
               OR configuration->>'source_slippage_model_id' IS DISTINCT FROM
                    research_row.artifact_payload#>>'{specification,slippage_model_id}'
               OR NOT EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        research_row.artifact_payload->'model_output_sets'
                    ) AS model_output
                    WHERE model_output->>'model_id' = configuration->>'model_id'
               )
               OR (configuration->>'random_seed')::bigint IS DISTINCT FROM
                    (source_lineage->>'random_seed')::bigint
               OR (configuration->>'raw_trial_count')::integer IS DISTINCT FROM
                    (source_lineage->>'raw_trial_count')::integer
               OR (configuration->>'effective_trial_count')::numeric IS DISTINCT FROM
                    (source_lineage->>'effective_trial_count')::numeric THEN
                RAISE EXCEPTION 'Phase 10 source and transition lineage mismatch';
            END IF;
            IF NEW.outcome <> 'SIMULATED_COMPLETE' THEN
                RETURN NEW;
            END IF;
            IF policy_row.approval_policy_version_id IS NOT NULL THEN
                PERFORM pg_advisory_xact_lock(
                    hashtextextended('phase10-policy:' || policy_row.policy_id, 0)
                );
            END IF;
            IF scope_row.approval_scope_version_id IS NOT NULL THEN
                PERFORM pg_advisory_xact_lock(
                    hashtextextended('phase10-scope:' || scope_row.scope_id, 0)
                );
            END IF;
            SELECT * INTO authorization_row FROM approval_authorizations
            WHERE human_authorization_evidence_id = NEW.human_authorization_evidence_id
              AND authorization_sha256 = NEW.authorization_sha256;
            SELECT * INTO risk_row FROM approval_risk_inputs
            WHERE risk_input_id = NEW.risk_input_id
              AND risk_input_sha256 = NEW.risk_input_sha256;
            SELECT COALESCE(
                jsonb_agg(to_jsonb(revocation_id) ORDER BY revocation_id::text),
                '[]'::jsonb
            ) INTO current_revocations
            FROM approval_revocations
            WHERE human_authorization_evidence_id = NEW.human_authorization_evidence_id;
            IF source_row.outcome <> 'APPROVED_PAPER'
               OR transition_row.outcome <> 'APPROVED_PAPER'
               OR NEW.decision_time_utc > NEW.created_at_utc
               OR EXISTS (
                    SELECT 1 FROM approval_checks
                    WHERE assessment_id IN (
                        NEW.source_assessment_id, NEW.transition_assessment_id
                    ) AND status <> 'PASS'
               )
               OR current_revocations IS DISTINCT FROM transition_row.revocation_ids
               OR policy_row.approval_policy_version_id IS NULL
               OR scope_row.approval_scope_version_id IS NULL
               OR authorization_row.human_authorization_evidence_id IS NULL
               OR risk_row.risk_input_id IS NULL
               OR NOT (
                    policy_row.valid_from_utc <= NEW.decision_time_utc
                    AND NEW.decision_time_utc < policy_row.expires_at_utc
                    AND NEW.created_at_utc < policy_row.expires_at_utc
               )
               OR NOT (
                    scope_row.valid_from_utc <= NEW.decision_time_utc
                    AND NEW.decision_time_utc < scope_row.expires_at_utc
                    AND NEW.created_at_utc < scope_row.expires_at_utc
               )
               OR NOT (
                    authorization_row.authorized_at_utc <= NEW.decision_time_utc
                    AND NEW.decision_time_utc < authorization_row.review_at_utc
                    AND NEW.decision_time_utc < authorization_row.expires_at_utc
                    AND NEW.created_at_utc < authorization_row.review_at_utc
                    AND NEW.created_at_utc < authorization_row.expires_at_utc
               )
               OR EXTRACT(EPOCH FROM (
                    NEW.decision_time_utc - authorization_row.authorized_at_utc
                  )) > policy_row.authorization_max_age_seconds
               OR risk_row.observed_at_utc > NEW.decision_time_utc
               OR EXTRACT(EPOCH FROM (
                    NEW.created_at_utc - risk_row.observed_at_utc
                  )) > policy_row.risk_input_max_age_seconds
               OR risk_row.global_control_clear IS DISTINCT FROM TRUE
               OR risk_row.strategy_control_clear IS DISTINCT FROM TRUE
               OR risk_row.data_quality_control_clear IS DISTINCT FROM TRUE
               OR risk_row.market_calendar_open IS DISTINCT FROM TRUE
               OR risk_row.duplicate_context_clear IS DISTINCT FROM TRUE
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
               OR risk_row.turnover IS NULL OR risk_row.turnover > policy_row.max_turnover
               OR risk_row.volatility IS NULL OR risk_row.volatility > policy_row.max_volatility
               OR risk_row.daily_loss IS NULL OR risk_row.daily_loss > policy_row.max_daily_loss
               OR risk_row.drawdown IS NULL OR risk_row.drawdown > policy_row.max_drawdown
               OR (NEW.artifact_payload#>>
                    '{configuration,approved_proposed_notional}')::numeric
                    IS DISTINCT FROM risk_row.proposed_notional
               OR NEW.artifact_payload#>>'{configuration,mock_universe_id}'
                    IS DISTINCT FROM risk_row.universe_id
               OR EXISTS (
                    SELECT 1 FROM approval_revocations
                    WHERE human_authorization_evidence_id =
                            NEW.human_authorization_evidence_id
                      AND effective_at_utc <= NEW.created_at_utc
               )
               OR EXISTS (
                    SELECT 1 FROM approval_policies AS later
                    WHERE later.policy_id = policy_row.policy_id
                      AND later.policy_version > policy_row.policy_version
                      AND later.valid_from_utc <= NEW.created_at_utc
                      AND NEW.created_at_utc < later.expires_at_utc
               )
               OR EXISTS (
                    SELECT 1 FROM approval_scopes AS later
                    WHERE later.scope_id = scope_row.scope_id
                      AND later.scope_version > scope_row.scope_version
                      AND later.valid_from_utc <= NEW.created_at_utc
                      AND NEW.created_at_utc < later.expires_at_utc
               ) THEN
                RAISE EXCEPTION
                    'Phase 10 simulation authority is stale, revoked, mismatched, or unsafe';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase10_check_payload()
        RETURNS trigger AS $$
        BEGIN
            IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 9
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR NEW.payload->>'code' IS DISTINCT FROM NEW.code
               OR NEW.payload->>'status' IS DISTINCT FROM NEW.status
               OR NEW.payload->>'reason_code' IS DISTINCT FROM NEW.reason_code
               OR NEW.payload->>'observed_value' IS DISTINCT FROM NEW.observed_value
               OR NEW.payload->>'threshold_value' IS DISTINCT FROM NEW.threshold_value
               OR NEW.payload->'evidence_sha256s' IS DISTINCT FROM NEW.evidence_sha256s
               OR NEW.payload->>'check_sha256' IS DISTINCT FROM NEW.check_sha256
               OR phase6_domain_sha256(
                    'phase10-local-simulation-check-v1', NEW.payload - 'check_sha256'
                  ) IS DISTINCT FROM NEW.check_sha256 THEN
                RAISE EXCEPTION 'Phase 10 simulation check payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase10_ledger_payload()
        RETURNS trigger AS $$
        DECLARE
            run_row paper_simulation_runs%ROWTYPE;
            configuration jsonb;
        BEGIN
            SELECT * INTO run_row FROM paper_simulation_runs
            WHERE simulation_run_id = NEW.simulation_run_id
              AND artifact_sha256 = NEW.simulation_artifact_sha256;
            configuration := run_row.artifact_payload->'configuration';
            IF run_row.simulation_run_id IS NULL OR run_row.outcome <> 'SIMULATED_COMPLETE'
               OR (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 51
               OR (NEW.payload->>'simulation_run_id')::uuid
                    IS DISTINCT FROM NEW.simulation_run_id
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR (NEW.payload->>'ledger_entry_id')::uuid
                    IS DISTINCT FROM NEW.ledger_entry_id
               OR NEW.payload->>'ledger_entry_sha256' IS DISTINCT FROM NEW.ledger_entry_sha256
               OR (NEW.payload->>'mock_snapshot_id')::uuid
                    IS DISTINCT FROM NEW.mock_snapshot_id
               OR NEW.payload->>'mock_snapshot_sha256' IS DISTINCT FROM NEW.mock_snapshot_sha256
               OR (NEW.payload->>'mock_observation_id')::uuid
                    IS DISTINCT FROM NEW.mock_observation_id
               OR NEW.payload->>'mock_observation_sha256'
                    IS DISTINCT FROM NEW.mock_observation_sha256
               OR NEW.payload->>'entity_id' IS DISTINCT FROM NEW.entity_id
               OR NEW.payload->>'universe_id' IS DISTINCT FROM NEW.universe_id
               OR (NEW.payload->>'observed_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.observed_at_utc
               OR (NEW.payload->>'available_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.available_at_utc
               OR (NEW.payload->>'decision_time_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc
               OR NEW.payload->>'model_id' IS DISTINCT FROM NEW.model_id
               OR NEW.payload->>'signal_rule_id' IS DISTINCT FROM NEW.signal_rule_id
               OR (NEW.payload->>'signal_value')::numeric IS DISTINCT FROM NEW.signal_value
               OR NEW.payload->>'signal_state' IS DISTINCT FROM NEW.signal_state
               OR NEW.payload->>'simulated_side' IS DISTINCT FROM NEW.simulated_side
               OR NEW.payload->>'fill_status' IS DISTINCT FROM NEW.fill_status
               OR (NEW.payload->>'approved_proposed_notional')::numeric
                    IS DISTINCT FROM NEW.approved_proposed_notional
               OR (NEW.payload->>'requested_quantity')::numeric
                    IS DISTINCT FROM NEW.requested_quantity
               OR (NEW.payload->>'filled_quantity')::numeric
                    IS DISTINCT FROM NEW.filled_quantity
               OR (NEW.payload->>'rejected_quantity')::numeric
                    IS DISTINCT FROM NEW.rejected_quantity
               OR (NEW.payload->>'unfilled_quantity')::numeric
                    IS DISTINCT FROM NEW.unfilled_quantity
               OR (NEW.payload->>'reference_price')::numeric
                    IS DISTINCT FROM NEW.reference_price
               OR (NEW.payload->>'simulated_fill_price')::numeric
                    IS DISTINCT FROM NEW.simulated_fill_price
               OR (NEW.payload->>'average_daily_volume')::numeric
                    IS DISTINCT FROM NEW.average_daily_volume
               OR (NEW.payload->>'volatility')::numeric IS DISTINCT FROM NEW.volatility
               OR (NEW.payload->>'participation_rate')::numeric
                    IS DISTINCT FROM NEW.participation_rate
               OR (NEW.payload->>'commission_cost')::numeric
                    IS DISTINCT FROM NEW.commission_cost
               OR (NEW.payload->>'regulatory_fee_cost')::numeric
                    IS DISTINCT FROM NEW.regulatory_fee_cost
               OR (NEW.payload->>'spread_cost')::numeric IS DISTINCT FROM NEW.spread_cost
               OR (NEW.payload->>'impact_cost')::numeric IS DISTINCT FROM NEW.impact_cost
               OR (NEW.payload->>'latency_cost')::numeric IS DISTINCT FROM NEW.latency_cost
               OR (NEW.payload->>'borrow_cost')::numeric IS DISTINCT FROM NEW.borrow_cost
               OR (NEW.payload->>'capacity_cost')::numeric IS DISTINCT FROM NEW.capacity_cost
               OR (NEW.payload->>'total_cost')::numeric IS DISTINCT FROM NEW.total_cost
               OR (NEW.payload->>'position_quantity_before')::numeric
                    IS DISTINCT FROM NEW.position_quantity_before
               OR (NEW.payload->>'position_quantity_after')::numeric
                    IS DISTINCT FROM NEW.position_quantity_after
               OR (NEW.payload->>'cash_before')::numeric IS DISTINCT FROM NEW.cash_before
               OR (NEW.payload->>'cash_after')::numeric IS DISTINCT FROM NEW.cash_after
               OR NEW.payload->>'source_transaction_cost_model_id'
                    IS DISTINCT FROM NEW.source_transaction_cost_model_id
               OR NEW.payload->>'source_slippage_model_id'
                    IS DISTINCT FROM NEW.source_slippage_model_id
               OR NEW.payload->>'local_cost_model_id'
                    IS DISTINCT FROM NEW.local_cost_model_id
               OR NEW.payload->>'local_slippage_model_id'
                    IS DISTINCT FROM NEW.local_slippage_model_id
               OR (NEW.payload->>'synthetic')::boolean IS DISTINCT FROM NEW.synthetic
               OR (NEW.payload->>'simulated_paper_only')::boolean
                    IS DISTINCT FROM NEW.simulated_paper_only
               OR (NEW.payload->>'local_mock_only')::boolean
                    IS DISTINCT FROM NEW.local_mock_only
               OR (NEW.payload->>'external_submission')::boolean
                    IS DISTINCT FROM NEW.external_submission
               OR (NEW.payload->>'live_path_absent')::boolean
                    IS DISTINCT FROM NEW.live_path_absent
               OR NEW.filled_quantity + NEW.unfilled_quantity <> NEW.requested_quantity
               OR NEW.rejected_quantity <> NEW.unfilled_quantity
               OR NEW.approved_proposed_notional
                    <> NEW.requested_quantity * NEW.reference_price
               OR NEW.participation_rate <> NEW.filled_quantity / NEW.average_daily_volume
               OR NEW.position_quantity_after
                    <> NEW.position_quantity_before + NEW.filled_quantity
               OR (NEW.simulated_fill_price - NEW.reference_price) * NEW.filled_quantity
                    <> NEW.spread_cost + NEW.impact_cost + NEW.latency_cost
               OR NEW.total_cost <> NEW.commission_cost + NEW.regulatory_fee_cost
                    + NEW.spread_cost + NEW.impact_cost + NEW.latency_cost
                    + NEW.borrow_cost + NEW.capacity_cost
               OR NEW.cash_after
                    <> NEW.cash_before - NEW.approved_proposed_notional - NEW.total_cost
               OR NOT (
                    NEW.observed_at_utc <= NEW.available_at_utc
                    AND NEW.available_at_utc <= NEW.decision_time_utc
               )
               OR NEW.decision_time_utc <> run_row.decision_time_utc
               OR NEW.mock_snapshot_id <>
                    (configuration->>'mock_snapshot_id')::uuid
               OR NEW.mock_snapshot_sha256
                    <> configuration->>'mock_snapshot_sha256'
               OR NEW.mock_observation_id <>
                    (configuration->>'mock_observation_id')::uuid
               OR NEW.mock_observation_sha256
                    <> configuration->>'mock_observation_sha256'
               OR NEW.entity_id <> configuration->>'mock_entity_id'
               OR NEW.universe_id <> configuration->>'mock_universe_id'
               OR NEW.observed_at_utc <>
                    (configuration->>'observed_at_utc')::timestamptz
               OR NEW.available_at_utc <>
                    (configuration->>'available_at_utc')::timestamptz
               OR NEW.model_id <> configuration->>'model_id'
               OR NEW.signal_rule_id <> configuration->>'signal_rule_id'
               OR NEW.signal_value <>
                    (configuration->>'synthetic_model_output')::numeric
               OR NEW.approved_proposed_notional <>
                    (configuration->>'approved_proposed_notional')::numeric
               OR NEW.requested_quantity <>
                    (configuration->>'requested_quantity')::numeric
               OR NEW.reference_price <> (configuration->>'reference_price')::numeric
               OR NEW.average_daily_volume <>
                    (configuration->>'average_daily_volume')::numeric
               OR NEW.volatility <> (configuration->>'volatility')::numeric
               OR NEW.cash_before <> (configuration->>'starting_cash')::numeric
               OR NEW.source_transaction_cost_model_id <>
                    configuration->>'source_transaction_cost_model_id'
               OR NEW.source_slippage_model_id <>
                    configuration->>'source_slippage_model_id'
               OR NEW.local_cost_model_id <> configuration->>'local_cost_model_id'
               OR NEW.local_slippage_model_id <>
                    configuration->>'local_slippage_model_id'
               OR NEW.signal_value <> 0.25::numeric
               OR NEW.simulated_fill_price <> NEW.reference_price + 0.04::numeric
               OR NEW.commission_cost <> NEW.filled_quantity * 0.01::numeric
               OR NEW.regulatory_fee_cost <> 0::numeric
               OR NEW.spread_cost <> NEW.filled_quantity * 0.02::numeric
               OR NEW.impact_cost <> NEW.filled_quantity * 0.01::numeric
               OR NEW.latency_cost <> NEW.filled_quantity * 0.01::numeric
               OR NEW.borrow_cost <> 0::numeric
               OR NEW.capacity_cost <> 0::numeric
               OR NEW.position_quantity_before <> 0::numeric
               OR phase6_domain_sha256(
                    'phase10-local-simulation-ledger-v1',
                    NEW.payload - ARRAY['ledger_entry_id','ledger_entry_sha256']::text[]
                  ) IS DISTINCT FROM NEW.ledger_entry_sha256
               OR phase6_uuid5(
                    '052c40b0-7781-57d9-942a-651518c41010'::uuid,
                    NEW.ledger_entry_sha256
                  ) IS DISTINCT FROM NEW.ledger_entry_id THEN
                RAISE EXCEPTION 'Phase 10 simulation ledger payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase10_simulation_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_run_id uuid;
            run_row paper_simulation_runs%ROWTYPE;
            check_count bigint;
            minimum_ordinal integer;
            maximum_ordinal integer;
            actual_codes jsonb;
            actual_checks jsonb;
            actual_ledger jsonb;
            all_pass boolean;
            actual_reasons jsonb;
            ledger_count bigint;
        BEGIN
            checked_run_id := NEW.simulation_run_id;
            SELECT * INTO run_row FROM paper_simulation_runs
            WHERE simulation_run_id = checked_run_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 10 completeness target is missing';
            END IF;
            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   bool_and(status = 'PASS')
            INTO check_count, minimum_ordinal, maximum_ordinal,
                 actual_codes, actual_checks, all_pass
            FROM paper_simulation_checks
            WHERE simulation_run_id = checked_run_id;
            SELECT count(*), COALESCE(
                jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb
            ) INTO ledger_count, actual_ledger
            FROM paper_simulation_ledger_entries
            WHERE simulation_run_id = checked_run_id;
            SELECT CASE
                WHEN all_pass THEN '["all_simulation_checks_passed"]'::jsonb
                ELSE COALESCE(
                    jsonb_agg(DISTINCT to_jsonb(reason_code) ORDER BY to_jsonb(reason_code))
                        FILTER (WHERE status <> 'PASS'),
                    '[]'::jsonb
                )
            END INTO actual_reasons
            FROM paper_simulation_checks
            WHERE simulation_run_id = checked_run_id;
            IF check_count <> {len(PHASE10_CHECK_CODES)}
               OR minimum_ordinal <> 1 OR maximum_ordinal <> {len(PHASE10_CHECK_CODES)}
               OR actual_codes IS DISTINCT FROM {_check_registry_json_sql()}
               OR NOT EXISTS (
                    SELECT 1 FROM paper_simulation_checks
                    WHERE simulation_run_id = checked_run_id
                      AND code = 'TRANSITION_APPROVAL_FRESH'
                      AND evidence_sha256s @>
                          jsonb_build_array(run_row.revalidation_proof_sha256)
               )
               OR actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'
               OR actual_ledger IS DISTINCT FROM run_row.artifact_payload->'ledger_entries'
               OR actual_reasons IS DISTINCT FROM run_row.reason_codes
               OR (run_row.outcome = 'SIMULATED_COMPLETE') IS DISTINCT FROM all_pass
               OR (
                    run_row.outcome = 'SIMULATED_COMPLETE' AND ledger_count <> 1
                  )
               OR (run_row.outcome = 'BLOCKED' AND ledger_count <> 0) THEN
                RAISE EXCEPTION
                    'Phase 10 simulation requires exact complete checks and ledger';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _install_validation_triggers() -> None:
    for table in AUTHORITY_LOCK_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_05_phase10_authority_lock
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION phase10_lock_authority_version()
            """
        )
    for table in PHASE10_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase10_created_at_utc()
            """
        )
    op.execute(
        """
        CREATE TRIGGER paper_simulation_runs_10_payload
        BEFORE INSERT ON paper_simulation_runs
        FOR EACH ROW EXECUTE FUNCTION validate_phase10_root_payload()
        """
    )
    op.execute(
        """
        CREATE TRIGGER paper_simulation_runs_20_authority
        BEFORE INSERT ON paper_simulation_runs
        FOR EACH ROW EXECUTE FUNCTION validate_phase10_current_authority()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER paper_simulation_runs_25_authority_commit
        AFTER INSERT ON paper_simulation_runs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase10_current_authority()
        """
    )
    op.execute(
        """
        CREATE TRIGGER paper_simulation_checks_10_payload
        BEFORE INSERT ON paper_simulation_checks
        FOR EACH ROW EXECUTE FUNCTION validate_phase10_check_payload()
        """
    )
    op.execute(
        """
        CREATE TRIGGER paper_simulation_ledger_entries_10_payload
        BEFORE INSERT ON paper_simulation_ledger_entries
        FOR EACH ROW EXECUTE FUNCTION validate_phase10_ledger_payload()
        """
    )
    for table in PHASE10_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase10_simulation_completeness()
            """
        )


def _install_append_only_guards() -> None:
    op.execute(
        f"""
        CREATE FUNCTION reject_phase10_paper_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '{PHASE10_APPEND_ONLY_ERROR}';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE10_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase10_paper_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase10_paper_mutation()
            """
        )


def downgrade() -> None:
    for table in AUTHORITY_LOCK_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_05_phase10_authority_lock ON {table}")
    for table in reversed(PHASE10_TABLES):
        op.drop_table(table)
    for function_name in (
        "reject_phase10_paper_mutation()",
        "validate_phase10_simulation_completeness()",
        "validate_phase10_ledger_payload()",
        "validate_phase10_check_payload()",
        "validate_phase10_current_authority()",
        "validate_phase10_root_payload()",
        "phase10_lock_authority_version()",
        "own_phase10_created_at_utc()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}")
