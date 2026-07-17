"""Add immutable external-paper shadow-readiness evidence.

Revision ID: 0009_phase12
Revises: 0008_phase10

This revision owns sanitized, read-only readiness evidence only.  It adds no
order, execution, broker-mutation, credential, or live-trading capability.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_phase12"
down_revision: str | None = "0008_phase10"
branch_labels: str | None = None
depends_on: str | None = None

PHASE12_TABLES = (
    "paper_shadow_readiness_runs",
    "paper_shadow_readiness_checks",
)

PHASE12_CHECK_CODES = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "ACCOUNT_READY",
    "MARKET_CLOCK_OPEN",
    "INSTRUMENT_ACTIVE_TRADABLE",
    "POSITIONS_EMPTY",
    "OPEN_ORDERS_EMPTY",
    "IEX_QUOTE_FRESH_VALID",
)

PHASE12_RUN_NAMESPACE = "f1195f7e-e891-5c21-9d3b-a0ced8881212"
PHASE12_APPEND_ONLY_ERROR = "Phase 12 paper shadow-readiness artifacts are append-only"


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


def _hash_check(columns: Iterable[str], *, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        " AND ".join(f"{column} ~ '^[0-9a-f]{{64}}$'" for column in columns),
        name=name,
    )


def _check_codes_sql() -> str:
    return ",".join(f"'{code}'" for code in PHASE12_CHECK_CODES)


def _check_registry_json_sql() -> str:
    return "'[" + ",".join(f'"{code}"' for code in PHASE12_CHECK_CODES) + "]'::jsonb"


def upgrade() -> None:
    op.create_table(
        "paper_shadow_readiness_runs",
        sa.Column("readiness_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("readiness_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("transport_profile_sha256", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("phase12_code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("assessment_started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessment_completed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_submission_authorized", sa.Boolean(), nullable=False),
        sa.Column("strategy_execution_eligible", sa.Boolean(), nullable=False),
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
                "transport_profile_sha256",
            ),
            name="ck_paper_shadow_readiness_run_hashes",
        ),
        sa.CheckConstraint(
            "artifact_schema_version = 'phase12-paper-shadow-readiness-v1' "
            "AND btrim(readiness_idempotency_key) <> '' "
            "AND source_kind IN ('DETERMINISTIC_MOCK','ALPACA_PAPER_READ_ONLY') "
            "AND transport_profile_sha256 = "
            "'0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c' "
            "AND outcome IN ('MOCK_PROOF_COMPLETE','SHADOW_READY','BLOCKED') "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) >= 1 "
            "AND phase12_code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND assessment_started_at_utc <= assessment_completed_at_utc "
            "AND expires_at_utc = assessment_completed_at_utc + interval '60 seconds' "
            "AND assessment_completed_at_utc <= created_at_utc "
            "AND (outcome <> 'SHADOW_READY' OR created_at_utc < expires_at_utc) "
            "AND NOT order_submission_authorized "
            "AND NOT strategy_execution_eligible "
            "AND live_path_absent "
            "AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND NOT (source_kind = 'DETERMINISTIC_MOCK' AND outcome = 'SHADOW_READY') "
            "AND NOT (source_kind = 'ALPACA_PAPER_READ_ONLY' "
            "         AND outcome = 'MOCK_PROOF_COMPLETE') "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_paper_shadow_readiness_run_boundary",
        ),
        sa.PrimaryKeyConstraint(
            "readiness_assessment_id",
            name="pk_paper_shadow_readiness_runs",
        ),
        sa.UniqueConstraint(
            "artifact_sha256",
            name="uq_paper_shadow_readiness_artifact",
        ),
        sa.UniqueConstraint(
            "request_fingerprint_sha256",
            name="uq_paper_shadow_readiness_request",
        ),
        sa.UniqueConstraint(
            "readiness_idempotency_key",
            name="uq_paper_shadow_readiness_idempotency",
        ),
        sa.UniqueConstraint(
            "readiness_assessment_id",
            "artifact_sha256",
            name="uq_paper_shadow_readiness_run_artifact",
        ),
    )

    op.create_table(
        "paper_shadow_readiness_checks",
        sa.Column("readiness_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("readiness_artifact_sha256", sa.String(length=64), nullable=False),
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
            ("readiness_artifact_sha256", "check_sha256"),
            name="ck_paper_shadow_readiness_check_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase12-paper-shadow-readiness-check-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE12_CHECK_CODES)} "
            f"AND code IN ({_check_codes_sql()}) "
            "AND status IN ('PASS','BLOCKED','UNCOMPUTABLE') "
            "AND btrim(reason_code) <> '' "
            "AND jsonb_typeof(evidence_sha256s) = 'array' "
            "AND jsonb_array_length(evidence_sha256s) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_paper_shadow_readiness_check_identity",
        ),
        sa.ForeignKeyConstraint(
            ["readiness_assessment_id", "readiness_artifact_sha256"],
            [
                "paper_shadow_readiness_runs.readiness_assessment_id",
                "paper_shadow_readiness_runs.artifact_sha256",
            ],
            name="fk_paper_shadow_readiness_check_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "readiness_assessment_id",
            "ordinal",
            name="pk_paper_shadow_readiness_checks",
        ),
        sa.UniqueConstraint(
            "readiness_assessment_id",
            "code",
            name="uq_paper_shadow_readiness_check_code",
        ),
        sa.UniqueConstraint(
            "readiness_assessment_id",
            "check_sha256",
            name="uq_paper_shadow_readiness_check_hash",
        ),
    )

    _install_validation_functions()
    _install_validation_triggers()
    _install_append_only_guards()


def _install_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION own_phase12_created_at_utc()
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
        CREATE FUNCTION phase12_lock_readiness_idempotency()
        RETURNS trigger AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(
                hashtextextended(
                    'phase12-readiness-workflow:' || NEW.readiness_idempotency_key,
                    0
                )
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase12_readiness_root_payload()
        RETURNS trigger AS $$
        DECLARE
            body jsonb;
            expected_request text;
            expected_artifact text;
        BEGIN
            body := NEW.artifact_payload;
            expected_request := phase6_domain_sha256(
                'phase12-paper-shadow-request-v1',
                jsonb_build_object(
                    'readiness_idempotency_key', NEW.readiness_idempotency_key,
                    'source_kind', NEW.source_kind,
                    'transport_profile_sha256', NEW.transport_profile_sha256,
                    'phase12_code_version_git_sha', NEW.phase12_code_version_git_sha
                )
            );
            expected_artifact := phase6_domain_sha256(
                'phase12-paper-shadow-artifact-v1', body
            );
            IF (SELECT count(*) FROM jsonb_object_keys(body)) <> 25
               OR NOT body ?& ARRAY[
                    'artifact_schema_version','request_fingerprint_sha256',
                    'readiness_idempotency_key','source_kind',
                    'transport_profile_sha256','inspections','account','clock',
                    'instrument','positions','open_orders','latest_quote','checks',
                    'outcome','reason_codes','phase12_code_version_git_sha',
                    'assessment_started_at_utc','assessment_completed_at_utc',
                    'expires_at_utc','order_submission_authorized',
                    'strategy_execution_eligible','live_path_absent',
                    'no_personalized_investment_advice',
                    'no_real_performance_claimed','disclaimer'
               ]
               OR jsonb_typeof(body->'inspections') <> 'array'
               OR jsonb_array_length(body->'inspections') <> 6
               OR body->>'artifact_schema_version'
                    IS DISTINCT FROM NEW.artifact_schema_version
               OR body->>'request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR body->>'readiness_idempotency_key'
                    IS DISTINCT FROM NEW.readiness_idempotency_key
               OR body->>'source_kind' IS DISTINCT FROM NEW.source_kind
               OR body->>'transport_profile_sha256'
                    IS DISTINCT FROM NEW.transport_profile_sha256
               OR body->>'outcome' IS DISTINCT FROM NEW.outcome
               OR body->'reason_codes' IS DISTINCT FROM NEW.reason_codes
               OR body->>'phase12_code_version_git_sha'
                    IS DISTINCT FROM NEW.phase12_code_version_git_sha
               OR (body->>'assessment_started_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.assessment_started_at_utc
               OR (body->>'assessment_completed_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.assessment_completed_at_utc
               OR (body->>'expires_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.expires_at_utc
               OR (body->>'order_submission_authorized')::boolean
                    IS DISTINCT FROM NEW.order_submission_authorized
               OR (body->>'strategy_execution_eligible')::boolean
                    IS DISTINCT FROM NEW.strategy_execution_eligible
               OR (body->>'live_path_absent')::boolean
                    IS DISTINCT FROM NEW.live_path_absent
               OR (body->>'no_personalized_investment_advice')::boolean
                    IS DISTINCT FROM NEW.no_personalized_investment_advice
               OR (body->>'no_real_performance_claimed')::boolean
                    IS DISTINCT FROM NEW.no_real_performance_claimed
               OR body->>'disclaimer' IS DISTINCT FROM
                    'PAPER ONLY shadow-readiness evidence; no order submission, strategy '
                    'execution, real performance claim, or personalized investment advice.'
               OR jsonb_typeof(body->'checks') <> 'array'
               OR expected_request IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR phase6_uuid5(
                    '{PHASE12_RUN_NAMESPACE}'::uuid,
                    expected_request
                  ) IS DISTINCT FROM NEW.readiness_assessment_id
               OR expected_artifact IS DISTINCT FROM NEW.artifact_sha256 THEN
                RAISE EXCEPTION 'Phase 12 readiness root payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase12_readiness_check_payload()
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
               OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(NEW.evidence_sha256s) AS evidence(value)
                    WHERE evidence.value !~ '^[0-9a-f]{64}$'
               )
               OR phase6_domain_sha256(
                    'phase12-paper-shadow-check-v1', NEW.payload - 'check_sha256'
                  ) IS DISTINCT FROM NEW.check_sha256 THEN
                RAISE EXCEPTION 'Phase 12 readiness check payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase12_readiness_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_assessment_id uuid;
            run_row paper_shadow_readiness_runs%ROWTYPE;
            check_count bigint;
            minimum_ordinal integer;
            maximum_ordinal integer;
            actual_codes jsonb;
            actual_checks jsonb;
            all_pass boolean;
            actual_reasons jsonb;
            expected_outcome text;
        BEGIN
            checked_assessment_id := NEW.readiness_assessment_id;
            SELECT * INTO run_row FROM paper_shadow_readiness_runs
            WHERE readiness_assessment_id = checked_assessment_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 12 readiness completeness target is missing';
            END IF;
            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO check_count, minimum_ordinal, maximum_ordinal,
                 actual_codes, actual_checks, all_pass
            FROM paper_shadow_readiness_checks
            WHERE readiness_assessment_id = checked_assessment_id;
            expected_outcome := CASE
                WHEN NOT all_pass THEN 'BLOCKED'
                WHEN run_row.source_kind = 'DETERMINISTIC_MOCK' THEN 'MOCK_PROOF_COMPLETE'
                ELSE 'SHADOW_READY'
            END;
            SELECT CASE
                WHEN all_pass AND run_row.source_kind = 'DETERMINISTIC_MOCK'
                    THEN '[\"all_mock_readiness_checks_passed\"]'::jsonb
                WHEN all_pass
                    THEN '[\"all_external_shadow_readiness_checks_passed\"]'::jsonb
                ELSE COALESCE(
                    jsonb_agg(DISTINCT to_jsonb(reason_code) ORDER BY to_jsonb(reason_code))
                        FILTER (WHERE status <> 'PASS'),
                    '[]'::jsonb
                )
            END INTO actual_reasons
            FROM paper_shadow_readiness_checks
            WHERE readiness_assessment_id = checked_assessment_id;
            IF check_count <> {len(PHASE12_CHECK_CODES)}
               OR minimum_ordinal <> 1
               OR maximum_ordinal <> {len(PHASE12_CHECK_CODES)}
               OR actual_codes IS DISTINCT FROM {_check_registry_json_sql()}
               OR actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'
               OR actual_reasons IS DISTINCT FROM run_row.reason_codes
               OR expected_outcome IS DISTINCT FROM run_row.outcome THEN
                RAISE EXCEPTION
                    'Phase 12 readiness requires exact complete ordered checks';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _install_validation_triggers() -> None:
    for table in PHASE12_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase12_created_at_utc()
            """
        )
    op.execute(
        """
        CREATE TRIGGER paper_shadow_readiness_runs_05_idempotency_lock
        BEFORE INSERT ON paper_shadow_readiness_runs
        FOR EACH ROW EXECUTE FUNCTION phase12_lock_readiness_idempotency()
        """
    )
    op.execute(
        """
        CREATE TRIGGER paper_shadow_readiness_runs_10_payload
        BEFORE INSERT ON paper_shadow_readiness_runs
        FOR EACH ROW EXECUTE FUNCTION validate_phase12_readiness_root_payload()
        """
    )
    op.execute(
        """
        CREATE TRIGGER paper_shadow_readiness_checks_10_payload
        BEFORE INSERT ON paper_shadow_readiness_checks
        FOR EACH ROW EXECUTE FUNCTION validate_phase12_readiness_check_payload()
        """
    )
    for table in PHASE12_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase12_readiness_completeness()
            """
        )


def _install_append_only_guards() -> None:
    op.execute(
        f"""
        CREATE FUNCTION reject_phase12_readiness_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '{PHASE12_APPEND_ONLY_ERROR}';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE12_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase12_readiness_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase12_readiness_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE12_TABLES):
        op.drop_table(table)
    for function_name in (
        "reject_phase12_readiness_mutation()",
        "validate_phase12_readiness_completeness()",
        "validate_phase12_readiness_check_payload()",
        "validate_phase12_readiness_root_payload()",
        "phase12_lock_readiness_idempotency()",
        "own_phase12_created_at_utc()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}")
