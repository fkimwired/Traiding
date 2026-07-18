"""Add immutable Phase 14 research-ingestion eligibility evidence.

Revision ID: 0011_phase14
Revises: 0010_phase13

This revision owns sanitized, database-only prerequisite assessments. It adds
no provider transport, licensed payload, research snapshot, performance,
promotion, approval, execution, order, or live-trading capability.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_phase14"
down_revision: str | None = "0010_phase13"
branch_labels: str | None = None
depends_on: str | None = None

PHASE14_TABLES = (
    "research_ingestion_eligibility_assessments",
    "research_ingestion_eligibility_payloads",
    "research_ingestion_eligibility_checks",
)

PHASE14_CAPABILITY_CODES = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)

PHASE14_CHECK_CODES = (
    "QUALIFICATION_IDENTITY_INTEGRITY",
    "QUALIFICATION_SOURCE_KIND_ALLOWED",
    "QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK",
    "CAPABILITY_MANIFEST_COMPLETE_PASSING",
    "QUALIFICATION_CHECKS_COMPLETE_PASSING",
    "EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK",
    "INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK",
    "USE_RIGHTS_CURRENT_OR_MOCK",
    "USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK",
    "LICENSED_PAYLOAD_ABSENT",
    "RESEARCH_SNAPSHOT_ABSENT",
    "PROMOTION_EXECUTION_AUTHORITY_ABSENT",
)

PHASE13_REASON_CODES = (
    "check_passed",
    "mock_rights_not_applicable",
    "credentials_unavailable",
    "rights_unavailable",
    "rights_not_current",
    "rights_insufficient",
    "capability_undocumented",
    "current_universe_only",
    "delisting_return_unavailable",
    "http_failure",
    "transport_failure",
    "redirect_rejected",
    "response_too_large",
    "malformed_utf8",
    "malformed_json",
    "duplicate_json_key",
    "non_finite_number",
    "schema_drift",
    "temporal_invalid",
    "identity_invalid",
    "action_revision_invalid",
    "fundamental_revision_invalid",
    "raw_normalized_mismatch",
    "null_sentinel_drift",
    "nondeterministic_capture",
    "prior_capability_blocked",
)

PHASE14_REASON_CODES = (
    "check_passed",
    "mock_not_applicable",
    "source_kind_not_allowed",
    "qualification_outcome_not_eligible",
    "capability_manifest_not_passing",
    "qualification_checks_not_passing",
    "external_request_evidence_incomplete",
    "independent_rights_reference_unverified",
    "rights_reference_missing",
    "rights_not_current",
    "rights_scope_insufficient",
    "authority_boundary_violation",
)

PHASE14_POLICY_SHA256 = "6952c310bd84cdbcf7fe96dd3c3d58efa1161b6c3f76d52e0fc174a6328a3c1c"
PHASE14_ASSESSMENT_NAMESPACE = "7eb85ca3-2d66-5e1e-b291-784b9352fe59"

PHASE14_APPEND_ONLY_ERROR = "Phase 14 research-ingestion eligibility artifacts are append-only"


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _json(column_name: str) -> sa.Column[object]:
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


def _codes_sql(codes: tuple[str, ...]) -> str:
    return ",".join(f"'{code}'" for code in codes)


def _registry_json_sql(codes: tuple[str, ...]) -> str:
    return "'[" + ",".join(f'"{code}"' for code in codes) + "]'::jsonb"


def upgrade() -> None:
    op.create_table(
        "research_ingestion_eligibility_assessments",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("assessment_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("policy_id", sa.String(length=128), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("qualification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "qualification_request_fingerprint_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("qualification_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "qualification_capture_manifest_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("qualification_source_kind", sa.String(length=40), nullable=False),
        sa.Column("qualification_outcome", sa.String(length=40), nullable=False),
        sa.Column(
            "qualification_rights_attestation_id",
            sa.String(length=256),
            nullable=True,
        ),
        sa.Column(
            "qualification_rights_attestation_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "qualification_code_version_git_sha",
            sa.String(length=40),
            nullable=False,
        ),
        _json("qualification_capability_manifest_sha256s"),
        _json("qualification_check_sha256s"),
        sa.Column("payload_manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("external_request_performed", sa.Boolean(), nullable=False),
        sa.Column("provider_payload_persisted", sa.Boolean(), nullable=False),
        sa.Column("research_ingestion_authorized", sa.Boolean(), nullable=False),
        sa.Column("research_snapshot_created", sa.Boolean(), nullable=False),
        sa.Column("research_data_eligible", sa.Boolean(), nullable=False),
        sa.Column("research_run_created", sa.Boolean(), nullable=False),
        sa.Column("research_run_authorized", sa.Boolean(), nullable=False),
        sa.Column("research_executed", sa.Boolean(), nullable=False),
        sa.Column("performance_computed", sa.Boolean(), nullable=False),
        sa.Column("pass_research_granted", sa.Boolean(), nullable=False),
        sa.Column("strategy_promotion_authorized", sa.Boolean(), nullable=False),
        sa.Column("paper_approval_granted", sa.Boolean(), nullable=False),
        sa.Column("strategy_execution_eligible", sa.Boolean(), nullable=False),
        sa.Column("execution_authorized", sa.Boolean(), nullable=False),
        sa.Column("order_submission_authorized", sa.Boolean(), nullable=False),
        sa.Column("live_path_absent", sa.Boolean(), nullable=False),
        sa.Column("no_personalized_investment_advice", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claimed", sa.Boolean(), nullable=False),
        _json("artifact_payload"),
        _created_at(),
        _hash_check(
            (
                "artifact_sha256",
                "request_fingerprint_sha256",
                "policy_sha256",
                "qualification_request_fingerprint_sha256",
                "qualification_artifact_sha256",
                "qualification_capture_manifest_sha256",
                "payload_manifest_sha256",
            ),
            name="ck_research_ingestion_eligibility_root_hashes",
        ),
        sa.CheckConstraint(
            "qualification_rights_attestation_sha256 IS NULL "
            "OR qualification_rights_attestation_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_research_ingestion_eligibility_rights_hash",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase14-research-ingestion-eligibility-v1' "
            "AND assessment_idempotency_key "
            "    ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$' "
            "AND policy_id = 'phase14-research-ingestion-eligibility-policy-v1' "
            f"AND policy_sha256 = '{PHASE14_POLICY_SHA256}' "
            "AND qualification_source_kind IN "
            "    ('DETERMINISTIC_MOCK','TIINGO_CANDIDATE_READ_ONLY') "
            "AND qualification_outcome IN "
            "    ('MOCK_PROOF_COMPLETE','EXTERNAL_SAMPLE_QUALIFIED','BLOCKED') "
            "AND outcome IN ('MOCK_PROOF_COMPLETE','BLOCKED') "
            "AND qualification_code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND jsonb_typeof(qualification_capability_manifest_sha256s) = 'array' "
            "AND jsonb_array_length(qualification_capability_manifest_sha256s) = 6 "
            "AND jsonb_typeof(qualification_check_sha256s) = 'array' "
            "AND jsonb_array_length(qualification_check_sha256s) = 12 "
            "AND ((qualification_source_kind = 'DETERMINISTIC_MOCK' "
            "      AND qualification_rights_attestation_id IS NULL "
            "      AND qualification_rights_attestation_sha256 IS NULL) "
            "  OR (qualification_source_kind = 'TIINGO_CANDIDATE_READ_ONLY' "
            "      AND qualification_rights_attestation_id "
            "          ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "      AND qualification_rights_attestation_sha256 IS NOT NULL)) "
            "AND started_at_utc <= completed_at_utc "
            "AND completed_at_utc <= created_at_utc "
            "AND NOT external_request_performed "
            "AND NOT provider_payload_persisted "
            "AND NOT research_ingestion_authorized "
            "AND NOT research_snapshot_created "
            "AND NOT research_data_eligible "
            "AND NOT research_run_created "
            "AND NOT research_run_authorized "
            "AND NOT research_executed "
            "AND NOT performance_computed "
            "AND NOT pass_research_granted "
            "AND NOT strategy_promotion_authorized "
            "AND NOT paper_approval_granted "
            "AND NOT strategy_execution_eligible "
            "AND NOT execution_authorized "
            "AND NOT order_submission_authorized "
            "AND live_path_absent "
            "AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND (outcome <> 'MOCK_PROOF_COMPLETE' "
            "     OR (qualification_source_kind = 'DETERMINISTIC_MOCK' "
            "         AND qualification_outcome = 'MOCK_PROOF_COMPLETE')) "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_research_ingestion_eligibility_root_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["qualification_id", "qualification_artifact_sha256"],
            [
                "point_in_time_qualification_runs.qualification_id",
                "point_in_time_qualification_runs.artifact_sha256",
            ],
            name="fk_research_ingestion_eligibility_qualification",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "assessment_id",
            name="pk_research_ingestion_eligibility_assessments",
        ),
        sa.UniqueConstraint(
            "artifact_sha256",
            name="uq_research_ingestion_eligibility_artifact",
        ),
        sa.UniqueConstraint(
            "request_fingerprint_sha256",
            name="uq_research_ingestion_eligibility_request",
        ),
        sa.UniqueConstraint(
            "assessment_idempotency_key",
            name="uq_research_ingestion_eligibility_idempotency",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "artifact_sha256",
            name="uq_research_ingestion_eligibility_assessment_artifact",
        ),
    )

    op.create_table(
        "research_ingestion_eligibility_payloads",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("source_status", sa.String(length=32), nullable=False),
        sa.Column("source_reason_code", sa.String(length=256), nullable=False),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_time_min_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_time_max_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at_min_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at_max_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("missingness_count", sa.Integer(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("raw_evidence_sha256", sa.String(length=64), nullable=True),
        sa.Column("normalized_evidence_sha256", sa.String(length=64), nullable=True),
        sa.Column("schema_identity_sha256", sa.String(length=64), nullable=True),
        sa.Column("request_evidence_count", sa.Integer(), nullable=False),
        _json("request_evidence_sha256s"),
        sa.Column(
            "source_capability_manifest_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        _json("payload"),
        _created_at(),
        _hash_check(
            (
                "assessment_artifact_sha256",
                "source_capability_manifest_sha256",
                "payload_sha256",
            ),
            name="ck_research_ingestion_eligibility_payload_hashes",
        ),
        sa.CheckConstraint(
            "(raw_evidence_sha256 IS NULL "
            " OR raw_evidence_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (normalized_evidence_sha256 IS NULL "
            " OR normalized_evidence_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (schema_identity_sha256 IS NULL "
            " OR schema_identity_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_research_ingestion_eligibility_payload_optional_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase14-research-ingestion-eligibility-payload-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE14_CAPABILITY_CODES)} "
            f"AND capability IN ({_codes_sql(PHASE14_CAPABILITY_CODES)}) "
            "AND source_status IN ('PASS','BLOCKED','UNCOMPUTABLE') "
            f"AND source_reason_code IN ({_codes_sql(PHASE13_REASON_CODES)}) "
            "AND record_count >= 0 AND missingness_count >= 0 "
            "AND revision_count >= 0 AND request_evidence_count >= 0 "
            "AND ((event_time_min_utc IS NULL AND event_time_max_utc IS NULL) "
            "     OR (event_time_min_utc IS NOT NULL AND event_time_max_utc IS NOT NULL "
            "         AND event_time_min_utc <= event_time_max_utc)) "
            "AND ((available_at_min_utc IS NULL AND available_at_max_utc IS NULL) "
            "     OR (available_at_min_utc IS NOT NULL "
            "         AND available_at_max_utc IS NOT NULL "
            "         AND available_at_min_utc <= available_at_max_utc "
            "         AND available_at_max_utc <= decision_time_utc)) "
            "AND jsonb_typeof(request_evidence_sha256s) = 'array' "
            "AND jsonb_array_length(request_evidence_sha256s) = request_evidence_count "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_research_ingestion_eligibility_payload_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id", "assessment_artifact_sha256"],
            [
                "research_ingestion_eligibility_assessments.assessment_id",
                "research_ingestion_eligibility_assessments.artifact_sha256",
            ],
            name="fk_research_ingestion_eligibility_payload_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "assessment_id",
            "ordinal",
            name="pk_research_ingestion_eligibility_payloads",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "capability",
            name="uq_research_ingestion_eligibility_payload_capability",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "payload_sha256",
            name="uq_research_ingestion_eligibility_payload_hash",
        ),
    )

    op.create_table(
        "research_ingestion_eligibility_checks",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=256), nullable=False),
        sa.Column("observed_value", sa.String(length=500), nullable=True),
        sa.Column("threshold_value", sa.String(length=500), nullable=True),
        _json("evidence_sha256s"),
        sa.Column("check_sha256", sa.String(length=64), nullable=False),
        _json("payload"),
        _created_at(),
        _hash_check(
            ("assessment_artifact_sha256", "check_sha256"),
            name="ck_research_ingestion_eligibility_check_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase14-research-ingestion-eligibility-check-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE14_CHECK_CODES)} "
            f"AND code IN ({_codes_sql(PHASE14_CHECK_CODES)}) "
            "AND status IN ('PASS','BLOCKED','UNCOMPUTABLE') "
            f"AND reason_code IN ({_codes_sql(PHASE14_REASON_CODES)}) "
            "AND reason_code !~ E'[\\n\\r]' "
            "AND (observed_value IS NULL OR (length(observed_value) BETWEEN 1 AND 256 "
            "     AND observed_value !~ E'[\\n\\r]' "
            "     AND lower(observed_value) !~ "
            "         'authorization|token|secret|api_key|apikey|\\?token=')) "
            "AND (threshold_value IS NULL OR (length(threshold_value) BETWEEN 1 AND 256 "
            "     AND threshold_value !~ E'[\\n\\r]' "
            "     AND lower(threshold_value) !~ "
            "         'authorization|token|secret|api_key|apikey|\\?token=')) "
            "AND jsonb_typeof(evidence_sha256s) = 'array' "
            "AND jsonb_array_length(evidence_sha256s) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_research_ingestion_eligibility_check_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id", "assessment_artifact_sha256"],
            [
                "research_ingestion_eligibility_assessments.assessment_id",
                "research_ingestion_eligibility_assessments.artifact_sha256",
            ],
            name="fk_research_ingestion_eligibility_check_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "assessment_id",
            "ordinal",
            name="pk_research_ingestion_eligibility_checks",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "code",
            name="uq_research_ingestion_eligibility_check_code",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "check_sha256",
            name="uq_research_ingestion_eligibility_check_hash",
        ),
    )

    _install_validation_functions()
    _install_validation_triggers()
    _install_append_only_guards()


def _install_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION own_phase14_created_at_utc()
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
        CREATE FUNCTION phase14_lock_eligibility_idempotency()
        RETURNS trigger AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(
                hashtextextended(
                    'phase14-eligibility-workflow:' || NEW.assessment_idempotency_key,
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
        CREATE FUNCTION validate_phase14_eligibility_root_payload()
        RETURNS trigger AS $$
        DECLARE
            body jsonb;
            source_row point_in_time_qualification_runs%ROWTYPE;
            source_profile jsonb;
            source_rights jsonb;
            expected_request text;
            expected_artifact text;
            source_expected_request text;
            source_expected_artifact text;
        BEGIN
            body := NEW.artifact_payload;
            SELECT * INTO source_row
            FROM point_in_time_qualification_runs
            WHERE qualification_id = NEW.qualification_id
              AND artifact_sha256 = NEW.qualification_artifact_sha256;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 14 qualification source is missing';
            END IF;
            source_profile := source_row.artifact_payload->'provider_profile';
            source_rights := source_row.artifact_payload->'rights_attestation';
            expected_request := phase6_domain_sha256(
                'phase14-research-ingestion-eligibility-request-v1',
                jsonb_build_object(
                    'schema_version', NEW.schema_version,
                    'qualification_id', NEW.qualification_id,
                    'policy_id', NEW.policy_id,
                    'policy_sha256', NEW.policy_sha256,
                    'code_version_git_sha', NEW.code_version_git_sha
                )
            );
            expected_artifact := phase6_domain_sha256(
                'phase14-research-ingestion-eligibility-artifact-v1', body
            );
            source_expected_request := phase6_domain_sha256(
                'phase13-pit-qualification-request-v1',
                jsonb_build_object(
                    'schema_version', source_row.schema_version,
                    'qualification_idempotency_key',
                        source_row.qualification_idempotency_key,
                    'source_kind', source_row.source_kind,
                    'provider_profile', source_profile,
                    'sample_plan_id', source_row.sample_plan_id,
                    'sample_plan_sha256', source_row.sample_plan_sha256,
                    'transport_profile_sha256', source_row.transport_profile_sha256,
                    'code_version_git_sha', source_row.code_version_git_sha
                )
            );
            source_expected_artifact := phase6_domain_sha256(
                'phase13-pit-qualification-artifact-v1', source_row.artifact_payload
            );

            IF (SELECT count(*) FROM jsonb_object_keys(body)) <> 43
               OR NOT body ?& ARRAY[
                    'schema_version','assessment_id','assessment_idempotency_key',
                    'request_fingerprint_sha256','policy_id','policy_sha256',
                    'qualification_id','qualification_request_fingerprint_sha256',
                    'qualification_artifact_sha256',
                    'qualification_capture_manifest_sha256',
                    'qualification_source_kind','qualification_outcome',
                    'qualification_rights_attestation_id',
                    'qualification_rights_attestation_sha256',
                    'qualification_code_version_git_sha',
                    'qualification_capability_manifest_sha256s',
                    'qualification_check_sha256s','payload_manifest_sha256',
                    'started_at_utc','completed_at_utc','code_version_git_sha',
                    'outcome','payloads','checks','external_request_performed',
                    'provider_payload_persisted','research_ingestion_authorized',
                    'research_snapshot_created','research_data_eligible',
                    'research_run_created','research_run_authorized',
                    'research_executed','performance_computed',
                    'pass_research_granted','strategy_promotion_authorized',
                    'paper_approval_granted','strategy_execution_eligible',
                    'execution_authorized','order_submission_authorized',
                    'live_path_absent','no_personalized_investment_advice',
                    'no_real_performance_claimed','disclaimer'
               ]
               OR body->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (body->>'assessment_id')::uuid IS DISTINCT FROM NEW.assessment_id
               OR body->>'assessment_idempotency_key'
                    IS DISTINCT FROM NEW.assessment_idempotency_key
               OR body->>'request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR body->>'policy_id' IS DISTINCT FROM NEW.policy_id
               OR body->>'policy_sha256' IS DISTINCT FROM NEW.policy_sha256
               OR (body->>'qualification_id')::uuid IS DISTINCT FROM NEW.qualification_id
               OR body->>'qualification_request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.qualification_request_fingerprint_sha256
               OR body->>'qualification_artifact_sha256'
                    IS DISTINCT FROM NEW.qualification_artifact_sha256
               OR body->>'qualification_capture_manifest_sha256'
                    IS DISTINCT FROM NEW.qualification_capture_manifest_sha256
               OR body->>'qualification_source_kind'
                    IS DISTINCT FROM NEW.qualification_source_kind
               OR body->>'qualification_outcome'
                    IS DISTINCT FROM NEW.qualification_outcome
               OR body->>'qualification_rights_attestation_id'
                    IS DISTINCT FROM NEW.qualification_rights_attestation_id
               OR body->>'qualification_rights_attestation_sha256'
                    IS DISTINCT FROM NEW.qualification_rights_attestation_sha256
               OR body->>'qualification_code_version_git_sha'
                    IS DISTINCT FROM NEW.qualification_code_version_git_sha
               OR body->'qualification_capability_manifest_sha256s'
                    IS DISTINCT FROM NEW.qualification_capability_manifest_sha256s
               OR body->'qualification_check_sha256s'
                    IS DISTINCT FROM NEW.qualification_check_sha256s
               OR body->>'payload_manifest_sha256'
                    IS DISTINCT FROM NEW.payload_manifest_sha256
               OR (body->>'started_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.started_at_utc
               OR (body->>'completed_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.completed_at_utc
               OR body->>'code_version_git_sha' IS DISTINCT FROM NEW.code_version_git_sha
               OR body->>'outcome' IS DISTINCT FROM NEW.outcome
               OR jsonb_typeof(body->'payloads') <> 'array'
               OR jsonb_typeof(body->'checks') <> 'array'
               OR (body->>'external_request_performed')::boolean
                    IS DISTINCT FROM NEW.external_request_performed
               OR (body->>'provider_payload_persisted')::boolean
                    IS DISTINCT FROM NEW.provider_payload_persisted
               OR (body->>'research_ingestion_authorized')::boolean
                    IS DISTINCT FROM NEW.research_ingestion_authorized
               OR (body->>'research_snapshot_created')::boolean
                    IS DISTINCT FROM NEW.research_snapshot_created
               OR (body->>'research_data_eligible')::boolean
                    IS DISTINCT FROM NEW.research_data_eligible
               OR (body->>'research_run_created')::boolean
                    IS DISTINCT FROM NEW.research_run_created
               OR (body->>'research_run_authorized')::boolean
                    IS DISTINCT FROM NEW.research_run_authorized
               OR (body->>'research_executed')::boolean
                    IS DISTINCT FROM NEW.research_executed
               OR (body->>'performance_computed')::boolean
                    IS DISTINCT FROM NEW.performance_computed
               OR (body->>'pass_research_granted')::boolean
                    IS DISTINCT FROM NEW.pass_research_granted
               OR (body->>'strategy_promotion_authorized')::boolean
                    IS DISTINCT FROM NEW.strategy_promotion_authorized
               OR (body->>'paper_approval_granted')::boolean
                    IS DISTINCT FROM NEW.paper_approval_granted
               OR (body->>'strategy_execution_eligible')::boolean
                    IS DISTINCT FROM NEW.strategy_execution_eligible
               OR (body->>'execution_authorized')::boolean
                    IS DISTINCT FROM NEW.execution_authorized
               OR (body->>'order_submission_authorized')::boolean
                    IS DISTINCT FROM NEW.order_submission_authorized
               OR (body->>'live_path_absent')::boolean
                    IS DISTINCT FROM NEW.live_path_absent
               OR (body->>'no_personalized_investment_advice')::boolean
                    IS DISTINCT FROM NEW.no_personalized_investment_advice
               OR (body->>'no_real_performance_claimed')::boolean
                    IS DISTINCT FROM NEW.no_real_performance_claimed
               OR body->>'disclaimer' IS DISTINCT FROM
                    'Eligibility-assessment evidence only; no research dataset, research '
                    'authorization, strategy result, promotion, execution authority, performance '
                    'claim, or personalized investment advice.'
               OR expected_request IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR phase6_uuid5(
                    '{PHASE14_ASSESSMENT_NAMESPACE}'::uuid, expected_request
                  ) IS DISTINCT FROM NEW.assessment_id
               OR expected_artifact IS DISTINCT FROM NEW.artifact_sha256
               OR NEW.policy_sha256 IS DISTINCT FROM '{PHASE14_POLICY_SHA256}'
               OR source_expected_request
                    IS DISTINCT FROM source_row.request_fingerprint_sha256
               OR phase6_uuid5(
                    '298dd99c-ab11-5c8b-98aa-866ebbb91313'::uuid,
                    source_expected_request
                  ) IS DISTINCT FROM source_row.qualification_id
               OR source_expected_artifact IS DISTINCT FROM source_row.artifact_sha256
               OR source_row.request_fingerprint_sha256
                    IS DISTINCT FROM NEW.qualification_request_fingerprint_sha256
               OR source_row.capture_manifest_sha256
                    IS DISTINCT FROM NEW.qualification_capture_manifest_sha256
               OR source_row.source_kind IS DISTINCT FROM NEW.qualification_source_kind
               OR source_row.outcome IS DISTINCT FROM NEW.qualification_outcome
               OR source_row.rights_attestation_id
                    IS DISTINCT FROM NEW.qualification_rights_attestation_id
               OR source_row.rights_attestation_sha256
                    IS DISTINCT FROM NEW.qualification_rights_attestation_sha256
               OR source_row.code_version_git_sha
                    IS DISTINCT FROM NEW.qualification_code_version_git_sha
               OR source_row.artifact_payload->>'schema_version'
                    IS DISTINCT FROM source_row.schema_version
               OR (source_row.artifact_payload->>'qualification_id')::uuid
                    IS DISTINCT FROM source_row.qualification_id
               OR source_row.artifact_payload->>'qualification_idempotency_key'
                    IS DISTINCT FROM source_row.qualification_idempotency_key
               OR source_row.artifact_payload->>'request_fingerprint_sha256'
                    IS DISTINCT FROM source_row.request_fingerprint_sha256
               OR source_row.artifact_payload->>'source_kind'
                    IS DISTINCT FROM source_row.source_kind
               OR source_row.artifact_payload->>'outcome'
                    IS DISTINCT FROM source_row.outcome
               OR source_row.artifact_payload->>'sample_plan_id'
                    IS DISTINCT FROM source_row.sample_plan_id
               OR source_row.artifact_payload->>'sample_plan_sha256'
                    IS DISTINCT FROM source_row.sample_plan_sha256
               OR source_row.artifact_payload->>'transport_profile_sha256'
                    IS DISTINCT FROM source_row.transport_profile_sha256
               OR source_row.artifact_payload->>'capture_manifest_sha256'
                    IS DISTINCT FROM source_row.capture_manifest_sha256
               OR (source_row.artifact_payload->>'started_at_utc')::timestamptz
                    IS DISTINCT FROM source_row.started_at_utc
               OR (source_row.artifact_payload->>'completed_at_utc')::timestamptz
                    IS DISTINCT FROM source_row.completed_at_utc
               OR source_row.artifact_payload->>'code_version_git_sha'
                    IS DISTINCT FROM source_row.code_version_git_sha
               OR source_profile->>'source_kind' IS DISTINCT FROM source_row.source_kind
               OR source_profile->>'provider_id' IS DISTINCT FROM source_row.provider_id
               OR source_profile->>'adapter_id' IS DISTINCT FROM source_row.adapter_id
               OR source_profile->>'adapter_version' IS DISTINCT FROM source_row.adapter_version
               OR source_profile->>'dataset_id' IS DISTINCT FROM source_row.dataset_id
               OR source_profile->>'product_id' IS DISTINCT FROM source_row.product_id
               OR (source_profile->>'synthetic')::boolean
                    IS DISTINCT FROM source_row.provider_synthetic
               OR (
                    source_rights IS NULL
                    AND (
                        source_row.rights_attestation_id IS NOT NULL
                        OR source_row.rights_attestation_sha256 IS NOT NULL
                    )
               )
               OR (
                    source_rights IS NOT NULL
                    AND (
                        source_rights->>'attestation_id'
                            IS DISTINCT FROM source_row.rights_attestation_id
                        OR source_rights->>'attestation_sha256'
                            IS DISTINCT FROM source_row.rights_attestation_sha256
                        OR (source_rights->>'valid_from_utc')::timestamptz
                            IS DISTINCT FROM source_row.rights_valid_from_utc
                        OR (source_rights->>'expires_at_utc')::timestamptz
                            IS DISTINCT FROM source_row.rights_expires_at_utc
                        OR (source_rights->>'storage_allowed')::boolean
                            IS DISTINCT FROM source_row.rights_storage_allowed
                        OR (source_rights->>'non_display_allowed')::boolean
                            IS DISTINCT FROM source_row.rights_non_display_allowed
                        OR (source_rights->>'derived_data_allowed')::boolean
                            IS DISTINCT FROM source_row.rights_derived_data_allowed
                    )
               )
               OR source_row.research_data_eligible
               OR source_row.strategy_promotion_authorized
               OR source_row.strategy_execution_eligible
               OR source_row.execution_authorized
               OR source_row.order_submission_authorized
               OR (source_row.artifact_payload->>'research_data_eligible')::boolean
                    IS DISTINCT FROM source_row.research_data_eligible
               OR (source_row.artifact_payload->>'strategy_promotion_authorized')::boolean
                    IS DISTINCT FROM source_row.strategy_promotion_authorized
               OR (source_row.artifact_payload->>'strategy_execution_eligible')::boolean
                    IS DISTINCT FROM source_row.strategy_execution_eligible
               OR (source_row.artifact_payload->>'execution_authorized')::boolean
                    IS DISTINCT FROM source_row.execution_authorized
               OR (source_row.artifact_payload->>'order_submission_authorized')::boolean
                    IS DISTINCT FROM source_row.order_submission_authorized
               OR (source_row.artifact_payload->>'live_path_absent')::boolean
                    IS DISTINCT FROM source_row.live_path_absent
               OR (source_row.artifact_payload->>'no_personalized_investment_advice')::boolean
                    IS DISTINCT FROM source_row.no_personalized_investment_advice
               OR (source_row.artifact_payload->>'no_real_performance_claimed')::boolean
                    IS DISTINCT FROM source_row.no_real_performance_claimed
               OR NOT source_row.live_path_absent
               OR NOT source_row.no_personalized_investment_advice
               OR NOT source_row.no_real_performance_claimed THEN
                RAISE EXCEPTION 'Phase 14 eligibility root or source payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase14_eligibility_payload()
        RETURNS trigger AS $$
        DECLARE
            canonical_evidence jsonb;
        BEGIN
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO canonical_evidence
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements_text(NEW.request_evidence_sha256s)
                    AS evidence(value)
            ) AS values;
            IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 20
               OR NOT NEW.payload ?& ARRAY[
                    'schema_version','ordinal','capability','source_status',
                    'source_reason_code','decision_time_utc','event_time_min_utc',
                    'event_time_max_utc','available_at_min_utc','available_at_max_utc',
                    'record_count','missingness_count','revision_count',
                    'raw_evidence_sha256','normalized_evidence_sha256',
                    'schema_identity_sha256','request_evidence_count',
                    'request_evidence_sha256s','source_capability_manifest_sha256',
                    'payload_sha256'
               ]
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR NEW.payload->>'capability' IS DISTINCT FROM NEW.capability
               OR NEW.payload->>'source_status' IS DISTINCT FROM NEW.source_status
               OR NEW.payload->>'source_reason_code'
                    IS DISTINCT FROM NEW.source_reason_code
               OR (NEW.payload->>'decision_time_utc')::timestamptz
                    IS DISTINCT FROM NEW.decision_time_utc
               OR (NEW.payload->>'event_time_min_utc')::timestamptz
                    IS DISTINCT FROM NEW.event_time_min_utc
               OR (NEW.payload->>'event_time_max_utc')::timestamptz
                    IS DISTINCT FROM NEW.event_time_max_utc
               OR (NEW.payload->>'available_at_min_utc')::timestamptz
                    IS DISTINCT FROM NEW.available_at_min_utc
               OR (NEW.payload->>'available_at_max_utc')::timestamptz
                    IS DISTINCT FROM NEW.available_at_max_utc
               OR (NEW.payload->>'record_count')::integer IS DISTINCT FROM NEW.record_count
               OR (NEW.payload->>'missingness_count')::integer
                    IS DISTINCT FROM NEW.missingness_count
               OR (NEW.payload->>'revision_count')::integer
                    IS DISTINCT FROM NEW.revision_count
               OR NEW.payload->>'raw_evidence_sha256'
                    IS DISTINCT FROM NEW.raw_evidence_sha256
               OR NEW.payload->>'normalized_evidence_sha256'
                    IS DISTINCT FROM NEW.normalized_evidence_sha256
               OR NEW.payload->>'schema_identity_sha256'
                    IS DISTINCT FROM NEW.schema_identity_sha256
               OR (NEW.payload->>'request_evidence_count')::integer
                    IS DISTINCT FROM NEW.request_evidence_count
               OR NEW.payload->'request_evidence_sha256s'
                    IS DISTINCT FROM NEW.request_evidence_sha256s
               OR NEW.payload->>'source_capability_manifest_sha256'
                    IS DISTINCT FROM NEW.source_capability_manifest_sha256
               OR NEW.payload->>'payload_sha256' IS DISTINCT FROM NEW.payload_sha256
               OR NEW.request_evidence_sha256s IS DISTINCT FROM canonical_evidence
               OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(NEW.request_evidence_sha256s)
                        AS evidence(value)
                    WHERE evidence.value !~ '^[0-9a-f]{64}$'
               )
               OR phase6_domain_sha256(
                    'phase14-research-ingestion-eligibility-payload-v1',
                    NEW.payload - 'payload_sha256'
                  ) IS DISTINCT FROM NEW.payload_sha256 THEN
                RAISE EXCEPTION 'Phase 14 eligibility payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase14_eligibility_check_payload()
        RETURNS trigger AS $$
        DECLARE
            canonical_evidence jsonb;
        BEGIN
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO canonical_evidence
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements_text(NEW.evidence_sha256s) AS evidence(value)
            ) AS values;
            IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 9
               OR NOT NEW.payload ?& ARRAY[
                    'schema_version','ordinal','code','status','reason_code',
                    'observed_value','threshold_value','evidence_sha256s','check_sha256'
               ]
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR NEW.payload->>'code' IS DISTINCT FROM NEW.code
               OR NEW.payload->>'status' IS DISTINCT FROM NEW.status
               OR NEW.payload->>'reason_code' IS DISTINCT FROM NEW.reason_code
               OR NEW.payload->>'observed_value' IS DISTINCT FROM NEW.observed_value
               OR NEW.payload->>'threshold_value' IS DISTINCT FROM NEW.threshold_value
               OR NEW.payload->'evidence_sha256s' IS DISTINCT FROM NEW.evidence_sha256s
               OR NEW.payload->>'check_sha256' IS DISTINCT FROM NEW.check_sha256
               OR NEW.evidence_sha256s IS DISTINCT FROM canonical_evidence
               OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(NEW.evidence_sha256s) AS evidence(value)
                    WHERE evidence.value !~ '^[0-9a-f]{64}$'
               )
               OR (NEW.status = 'PASS'
                   AND NEW.reason_code NOT IN ('check_passed','mock_not_applicable'))
               OR (NEW.status <> 'PASS'
                   AND NEW.reason_code IN ('check_passed','mock_not_applicable'))
               OR (NEW.reason_code = 'mock_not_applicable' AND NEW.code NOT IN (
                    'EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK',
                    'INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK',
                    'USE_RIGHTS_CURRENT_OR_MOCK',
                    'USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK'
               ))
               OR phase6_domain_sha256(
                    'phase14-research-ingestion-eligibility-check-v1',
                    NEW.payload - 'check_sha256'
                  ) IS DISTINCT FROM NEW.check_sha256 THEN
                RAISE EXCEPTION 'Phase 14 eligibility check payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase14_eligibility_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_assessment_id uuid;
            run_row research_ingestion_eligibility_assessments%ROWTYPE;
            source_row point_in_time_qualification_runs%ROWTYPE;
            payload_count bigint;
            payload_minimum_ordinal integer;
            payload_maximum_ordinal integer;
            actual_capabilities jsonb;
            actual_payloads jsonb;
            actual_payload_hashes jsonb;
            check_count bigint;
            check_minimum_ordinal integer;
            check_maximum_ordinal integer;
            actual_codes jsonb;
            actual_checks jsonb;
            checks_pass boolean;
            source_payload_count bigint;
            source_payload_minimum_ordinal integer;
            source_payload_maximum_ordinal integer;
            source_capabilities jsonb;
            source_payloads jsonb;
            source_capability_hashes jsonb;
            source_payloads_pass boolean;
            source_check_count bigint;
            source_check_minimum_ordinal integer;
            source_check_maximum_ordinal integer;
            source_codes jsonb;
            source_checks jsonb;
            source_check_hashes jsonb;
            source_checks_pass boolean;
            source_identity_evidence jsonb;
            source_artifact_request_evidence jsonb;
            source_artifact_capture_evidence jsonb;
            source_capability_evidence jsonb;
            source_check_evidence jsonb;
            source_request_evidence jsonb;
            source_artifact_payload_manifest_evidence jsonb;
            external_requests_complete boolean;
            source_rights_current boolean;
            source_rights_sufficient boolean;
            source_authority_absent boolean;
            expected_source_capture text;
            expected_source_outcome text;
            expected_payload_manifest text;
            expected_outcome text;
        BEGIN
            checked_assessment_id := NEW.assessment_id;
            SELECT * INTO run_row
            FROM research_ingestion_eligibility_assessments
            WHERE assessment_id = checked_assessment_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 14 eligibility completeness target is missing';
            END IF;
            SELECT * INTO source_row
            FROM point_in_time_qualification_runs
            WHERE qualification_id = run_row.qualification_id
              AND artifact_sha256 = run_row.qualification_artifact_sha256;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 14 qualification source is missing';
            END IF;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(capability) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(to_jsonb(payload_sha256) ORDER BY ordinal), '[]'::jsonb)
            INTO payload_count, payload_minimum_ordinal, payload_maximum_ordinal,
                 actual_capabilities, actual_payloads, actual_payload_hashes
            FROM research_ingestion_eligibility_payloads
            WHERE assessment_id = checked_assessment_id;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO check_count, check_minimum_ordinal, check_maximum_ordinal,
                 actual_codes, actual_checks, checks_pass
            FROM research_ingestion_eligibility_checks
            WHERE assessment_id = checked_assessment_id;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(capability) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(
                       jsonb_agg(to_jsonb(capability_manifest_sha256) ORDER BY ordinal),
                       '[]'::jsonb
                   ),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO source_payload_count, source_payload_minimum_ordinal,
                 source_payload_maximum_ordinal, source_capabilities, source_payloads,
                 source_capability_hashes, source_payloads_pass
            FROM point_in_time_qualification_payloads
            WHERE qualification_id = source_row.qualification_id;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(to_jsonb(check_sha256) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO source_check_count, source_check_minimum_ordinal,
                 source_check_maximum_ordinal, source_codes, source_checks,
                 source_check_hashes, source_checks_pass
            FROM point_in_time_qualification_checks
            WHERE qualification_id = source_row.qualification_id;

            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_identity_evidence
            FROM (
                SELECT DISTINCT unnest(ARRAY[
                    source_row.request_fingerprint_sha256,
                    source_row.artifact_sha256,
                    source_row.capture_manifest_sha256
                ]) AS value
            ) AS evidence;
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_artifact_request_evidence
            FROM (
                SELECT DISTINCT unnest(ARRAY[
                    source_row.artifact_sha256,
                    source_row.request_fingerprint_sha256
                ]) AS value
            ) AS evidence;
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_artifact_capture_evidence
            FROM (
                SELECT DISTINCT unnest(ARRAY[
                    source_row.artifact_sha256,
                    source_row.capture_manifest_sha256
                ]) AS value
            ) AS evidence;
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_capability_evidence
            FROM (
                SELECT DISTINCT capability_manifest_sha256 AS value
                FROM point_in_time_qualification_payloads
                WHERE qualification_id = source_row.qualification_id
            ) AS evidence;
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_check_evidence
            FROM (
                SELECT DISTINCT check_sha256 AS value
                FROM point_in_time_qualification_checks
                WHERE qualification_id = source_row.qualification_id
            ) AS evidence;
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_request_evidence
            FROM (
                SELECT DISTINCT request_item->>'request_evidence_sha256' AS value
                FROM point_in_time_qualification_payloads AS source_payload
                CROSS JOIN LATERAL jsonb_array_elements(source_payload.request_evidence)
                    AS request(request_item)
                WHERE source_payload.qualification_id = source_row.qualification_id
            ) AS evidence;
            SELECT count(DISTINCT request_item->>'code') = 5
                   AND COALESCE(bool_and(
                       request_item->>'code' IN (
                           'FUNDAMENTALS_META','EOD_PRICES','DISTRIBUTIONS','SPLITS',
                           'FUNDAMENTAL_STATEMENTS'
                       )
                   ), false)
            INTO external_requests_complete
            FROM point_in_time_qualification_payloads AS source_payload
            CROSS JOIN LATERAL jsonb_array_elements(source_payload.request_evidence)
                AS request(request_item)
            WHERE source_payload.qualification_id = source_row.qualification_id
              AND (request_item->>'external_request_performed')::boolean
              AND request_item->>'status' = 'OBSERVED';
            SELECT COALESCE(jsonb_agg(to_jsonb(value) ORDER BY value), '[]'::jsonb)
            INTO source_artifact_payload_manifest_evidence
            FROM (
                SELECT DISTINCT unnest(ARRAY[
                    source_row.artifact_sha256,
                    run_row.payload_manifest_sha256
                ]) AS value
            ) AS evidence;
            source_rights_current := COALESCE(
                source_row.rights_valid_from_utc <= run_row.completed_at_utc
                AND run_row.completed_at_utc < source_row.rights_expires_at_utc,
                false
            );
            source_rights_sufficient := COALESCE(
                source_row.rights_storage_allowed
                AND source_row.rights_non_display_allowed
                AND source_row.rights_derived_data_allowed,
                false
            );
            source_authority_absent :=
                NOT source_row.research_data_eligible
                AND NOT source_row.strategy_promotion_authorized
                AND NOT source_row.strategy_execution_eligible
                AND NOT source_row.execution_authorized
                AND NOT source_row.order_submission_authorized
                AND source_row.live_path_absent
                AND source_row.no_personalized_investment_advice
                AND source_row.no_real_performance_claimed;

            expected_source_capture := phase6_domain_sha256(
                'phase13-pit-capture-manifest-v1',
                jsonb_build_object(
                    'provider_profile', source_row.artifact_payload->'provider_profile',
                    'rights_attestation', source_row.artifact_payload->'rights_attestation',
                    'sample_plan_id', source_row.sample_plan_id,
                    'sample_plan_sha256', source_row.sample_plan_sha256,
                    'capability_manifest_sha256s', source_capability_hashes
                )
            );
            expected_source_outcome := CASE
                WHEN NOT (source_payloads_pass AND source_checks_pass) THEN 'BLOCKED'
                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                    THEN 'MOCK_PROOF_COMPLETE'
                ELSE 'EXTERNAL_SAMPLE_QUALIFIED'
            END;
            expected_payload_manifest := phase6_domain_sha256(
                'phase14-research-ingestion-eligibility-payload-manifest-v1',
                jsonb_build_object(
                    'schema_version',
                        'phase14-research-ingestion-eligibility-payload-v1',
                    'payload_sha256s', actual_payload_hashes
                )
            );
            expected_outcome := CASE
                WHEN run_row.qualification_source_kind = 'DETERMINISTIC_MOCK'
                     AND run_row.qualification_outcome = 'MOCK_PROOF_COMPLETE'
                     AND checks_pass
                    THEN 'MOCK_PROOF_COMPLETE'
                ELSE 'BLOCKED'
            END;

            IF payload_count <> {len(PHASE14_CAPABILITY_CODES)}
               OR payload_minimum_ordinal <> 1
               OR payload_maximum_ordinal <> {len(PHASE14_CAPABILITY_CODES)}
               OR actual_capabilities IS DISTINCT FROM
                    {_registry_json_sql(PHASE14_CAPABILITY_CODES)}
               OR actual_payloads IS DISTINCT FROM run_row.artifact_payload->'payloads'
               OR check_count <> {len(PHASE14_CHECK_CODES)}
               OR check_minimum_ordinal <> 1
               OR check_maximum_ordinal <> {len(PHASE14_CHECK_CODES)}
               OR actual_codes IS DISTINCT FROM {_registry_json_sql(PHASE14_CHECK_CODES)}
               OR actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'
               OR expected_payload_manifest IS DISTINCT FROM run_row.payload_manifest_sha256
               OR expected_outcome IS DISTINCT FROM run_row.outcome
               OR (run_row.outcome = 'BLOCKED' AND checks_pass)
               OR source_payload_count <> {len(PHASE14_CAPABILITY_CODES)}
               OR source_payload_minimum_ordinal <> 1
               OR source_payload_maximum_ordinal <> {len(PHASE14_CAPABILITY_CODES)}
               OR source_capabilities IS DISTINCT FROM
                    {_registry_json_sql(PHASE14_CAPABILITY_CODES)}
               OR source_payloads IS DISTINCT FROM
                    source_row.artifact_payload->'capability_manifests'
               OR source_check_count <> 12
               OR source_check_minimum_ordinal <> 1
               OR source_check_maximum_ordinal <> 12
               OR source_codes IS DISTINCT FROM
                    '["SOURCE_KIND_EXACT","READ_ONLY_TRANSPORT_EXACT",'
                    '"USE_RIGHTS_CURRENT_SUFFICIENT",'
                    '"SECURITY_MASTER_STABLE_IDENTITY",'
                    '"POINT_IN_TIME_UNIVERSE_MEMBERSHIP","RAW_OHLCV_AVAILABILITY",'
                    '"CORPORATE_ACTION_ANNOUNCEMENT_REVISION",'
                    '"DELISTING_RETURN_SEMANTICS",'
                    '"AS_REPORTED_FUNDAMENTAL_REVISION",'
                    '"RAW_NORMALIZED_RECONCILIATION",'
                    '"NULL_SENTINEL_SCHEMA_DRIFT",'
                    '"DETERMINISTIC_CAPTURE_MANIFEST"]'::jsonb
               OR source_checks IS DISTINCT FROM source_row.artifact_payload->'checks'
               OR source_capability_hashes IS DISTINCT FROM
                    run_row.qualification_capability_manifest_sha256s
               OR source_check_hashes IS DISTINCT FROM run_row.qualification_check_sha256s
               OR expected_source_capture IS DISTINCT FROM source_row.capture_manifest_sha256
               OR expected_source_outcome IS DISTINCT FROM source_row.outcome
               OR EXISTS (
                    SELECT 1
                    FROM point_in_time_qualification_payloads AS source_payload
                    WHERE source_payload.qualification_id = source_row.qualification_id
                      AND (
                        phase6_domain_sha256(
                            'phase13-pit-capability-manifest-v1',
                            source_payload.payload - 'capability_manifest_sha256'
                        ) IS DISTINCT FROM source_payload.capability_manifest_sha256
                        OR source_payload.payload->>'schema_version'
                            IS DISTINCT FROM source_payload.schema_version
                        OR (source_payload.payload->>'ordinal')::integer
                            IS DISTINCT FROM source_payload.ordinal
                        OR source_payload.payload->>'capability'
                            IS DISTINCT FROM source_payload.capability
                        OR source_payload.payload->>'status'
                            IS DISTINCT FROM source_payload.status
                        OR source_payload.payload->>'reason_code'
                            IS DISTINCT FROM source_payload.reason_code
                        OR (source_payload.payload->>'decision_time_utc')::timestamptz
                            IS DISTINCT FROM source_payload.decision_time_utc
                        OR (source_payload.payload->>'event_time_min_utc')::timestamptz
                            IS DISTINCT FROM source_payload.event_time_min_utc
                        OR (source_payload.payload->>'event_time_max_utc')::timestamptz
                            IS DISTINCT FROM source_payload.event_time_max_utc
                        OR (source_payload.payload->>'available_at_min_utc')::timestamptz
                            IS DISTINCT FROM source_payload.available_at_min_utc
                        OR (source_payload.payload->>'available_at_max_utc')::timestamptz
                            IS DISTINCT FROM source_payload.available_at_max_utc
                        OR (source_payload.payload->>'record_count')::integer
                            IS DISTINCT FROM source_payload.record_count
                        OR (source_payload.payload->>'missingness_count')::integer
                            IS DISTINCT FROM source_payload.missingness_count
                        OR (source_payload.payload->>'revision_count')::integer
                            IS DISTINCT FROM source_payload.revision_count
                        OR source_payload.payload->>'raw_evidence_sha256'
                            IS DISTINCT FROM source_payload.raw_evidence_sha256
                        OR source_payload.payload->>'normalized_evidence_sha256'
                            IS DISTINCT FROM source_payload.normalized_evidence_sha256
                        OR source_payload.payload->>'schema_identity_sha256'
                            IS DISTINCT FROM source_payload.schema_identity_sha256
                        OR source_payload.payload->'request_evidence'
                            IS DISTINCT FROM source_payload.request_evidence
                        OR source_payload.payload->>'capability_manifest_sha256'
                            IS DISTINCT FROM source_payload.capability_manifest_sha256
                      )
               )
               OR EXISTS (
                    SELECT 1
                    FROM point_in_time_qualification_payloads AS source_payload
                    CROSS JOIN LATERAL jsonb_array_elements(source_payload.request_evidence)
                        AS request(request_item)
                    WHERE source_payload.qualification_id = source_row.qualification_id
                      AND phase6_domain_sha256(
                            'phase13-pit-request-evidence-v1',
                            request_item - 'request_evidence_sha256'
                          ) IS DISTINCT FROM request_item->>'request_evidence_sha256'
               )
               OR EXISTS (
                    SELECT 1
                    FROM point_in_time_qualification_checks AS source_check
                    WHERE source_check.qualification_id = source_row.qualification_id
                      AND (
                        phase6_domain_sha256(
                            'phase13-pit-qualification-check-v1',
                            source_check.payload - 'check_sha256'
                        ) IS DISTINCT FROM source_check.check_sha256
                        OR source_check.payload->>'schema_version'
                            IS DISTINCT FROM source_check.schema_version
                        OR (source_check.payload->>'ordinal')::integer
                            IS DISTINCT FROM source_check.ordinal
                        OR source_check.payload->>'code' IS DISTINCT FROM source_check.code
                        OR source_check.payload->>'status'
                            IS DISTINCT FROM source_check.status
                        OR source_check.payload->>'reason_code'
                            IS DISTINCT FROM source_check.reason_code
                        OR source_check.payload->>'observed_value'
                            IS DISTINCT FROM source_check.observed_value
                        OR source_check.payload->>'threshold_value'
                            IS DISTINCT FROM source_check.threshold_value
                        OR source_check.payload->'evidence_sha256s'
                            IS DISTINCT FROM source_check.evidence_sha256s
                        OR source_check.payload->>'check_sha256'
                            IS DISTINCT FROM source_check.check_sha256
                      )
               )
               OR EXISTS (
                    SELECT 1
                    FROM research_ingestion_eligibility_payloads AS projected
                    JOIN point_in_time_qualification_payloads AS source_payload
                      ON source_payload.qualification_id = source_row.qualification_id
                     AND source_payload.ordinal = projected.ordinal
                    WHERE projected.assessment_id = checked_assessment_id
                      AND (
                        projected.capability IS DISTINCT FROM source_payload.capability
                        OR projected.source_status IS DISTINCT FROM source_payload.status
                        OR projected.source_reason_code IS DISTINCT FROM source_payload.reason_code
                        OR projected.decision_time_utc
                            IS DISTINCT FROM source_payload.decision_time_utc
                        OR projected.event_time_min_utc
                            IS DISTINCT FROM source_payload.event_time_min_utc
                        OR projected.event_time_max_utc
                            IS DISTINCT FROM source_payload.event_time_max_utc
                        OR projected.available_at_min_utc
                            IS DISTINCT FROM source_payload.available_at_min_utc
                        OR projected.available_at_max_utc
                            IS DISTINCT FROM source_payload.available_at_max_utc
                        OR projected.record_count IS DISTINCT FROM source_payload.record_count
                        OR projected.missingness_count
                            IS DISTINCT FROM source_payload.missingness_count
                        OR projected.revision_count IS DISTINCT FROM source_payload.revision_count
                        OR projected.raw_evidence_sha256
                            IS DISTINCT FROM source_payload.raw_evidence_sha256
                        OR projected.normalized_evidence_sha256
                            IS DISTINCT FROM source_payload.normalized_evidence_sha256
                        OR projected.schema_identity_sha256
                            IS DISTINCT FROM source_payload.schema_identity_sha256
                        OR projected.request_evidence_count
                            IS DISTINCT FROM jsonb_array_length(source_payload.request_evidence)
                        OR projected.request_evidence_sha256s IS DISTINCT FROM COALESCE(
                            (
                                SELECT jsonb_agg(
                                    request_item->'request_evidence_sha256'
                                    ORDER BY request_item->>'request_evidence_sha256'
                                )
                                FROM jsonb_array_elements(source_payload.request_evidence)
                                    AS request(request_item)
                            ),
                            '[]'::jsonb
                        )
                        OR projected.source_capability_manifest_sha256
                            IS DISTINCT FROM source_payload.capability_manifest_sha256
                      )
               )
               OR EXISTS (
                    SELECT 1
                    FROM research_ingestion_eligibility_checks AS policy_check
                    WHERE policy_check.assessment_id = checked_assessment_id
                      AND (
                        policy_check.status IS DISTINCT FROM CASE policy_check.ordinal
                            WHEN 1 THEN 'PASS'
                            WHEN 2 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'PASS'
                                ELSE 'BLOCKED'
                            END
                            WHEN 3 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     AND source_row.outcome = 'MOCK_PROOF_COMPLETE'
                                    THEN 'PASS'
                                ELSE 'BLOCKED'
                            END
                            WHEN 4 THEN CASE
                                WHEN source_payloads_pass THEN 'PASS'
                                ELSE 'BLOCKED'
                            END
                            WHEN 5 THEN CASE
                                WHEN source_checks_pass THEN 'PASS'
                                ELSE 'BLOCKED'
                            END
                            WHEN 6 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     OR external_requests_complete
                                    THEN 'PASS'
                                ELSE 'UNCOMPUTABLE'
                            END
                            WHEN 7 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'PASS'
                                ELSE 'UNCOMPUTABLE'
                            END
                            WHEN 8 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'PASS'
                                WHEN source_row.rights_attestation_sha256 IS NOT NULL
                                     AND NOT source_rights_current
                                    THEN 'BLOCKED'
                                ELSE 'UNCOMPUTABLE'
                            END
                            WHEN 9 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'PASS'
                                WHEN source_row.rights_attestation_sha256 IS NOT NULL
                                     AND NOT source_rights_sufficient
                                    THEN 'BLOCKED'
                                ELSE 'UNCOMPUTABLE'
                            END
                            WHEN 10 THEN 'PASS'
                            WHEN 11 THEN 'PASS'
                            WHEN 12 THEN CASE
                                WHEN source_authority_absent THEN 'PASS'
                                ELSE 'BLOCKED'
                            END
                        END
                        OR policy_check.reason_code IS DISTINCT FROM CASE policy_check.ordinal
                            WHEN 1 THEN 'check_passed'
                            WHEN 2 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'check_passed'
                                ELSE 'source_kind_not_allowed'
                            END
                            WHEN 3 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     AND source_row.outcome = 'MOCK_PROOF_COMPLETE'
                                    THEN 'check_passed'
                                ELSE 'qualification_outcome_not_eligible'
                            END
                            WHEN 4 THEN CASE
                                WHEN source_payloads_pass THEN 'check_passed'
                                ELSE 'capability_manifest_not_passing'
                            END
                            WHEN 5 THEN CASE
                                WHEN source_checks_pass THEN 'check_passed'
                                ELSE 'qualification_checks_not_passing'
                            END
                            WHEN 6 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock_not_applicable'
                                WHEN external_requests_complete THEN 'check_passed'
                                ELSE 'external_request_evidence_incomplete'
                            END
                            WHEN 7 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock_not_applicable'
                                WHEN source_row.rights_attestation_sha256 IS NULL
                                    THEN 'rights_reference_missing'
                                ELSE 'independent_rights_reference_unverified'
                            END
                            WHEN 8 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock_not_applicable'
                                WHEN source_row.rights_attestation_sha256 IS NULL
                                    THEN 'rights_reference_missing'
                                WHEN NOT source_rights_current THEN 'rights_not_current'
                                ELSE 'independent_rights_reference_unverified'
                            END
                            WHEN 9 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock_not_applicable'
                                WHEN source_row.rights_attestation_sha256 IS NULL
                                    THEN 'rights_reference_missing'
                                WHEN NOT source_rights_sufficient THEN 'rights_scope_insufficient'
                                ELSE 'independent_rights_reference_unverified'
                            END
                            WHEN 10 THEN 'check_passed'
                            WHEN 11 THEN 'check_passed'
                            WHEN 12 THEN CASE
                                WHEN source_authority_absent THEN 'check_passed'
                                ELSE 'authority_boundary_violation'
                            END
                        END
                        OR policy_check.observed_value IS DISTINCT FROM CASE policy_check.ordinal
                            WHEN 1 THEN 'valid'
                            WHEN 2 THEN source_row.source_kind
                            WHEN 3 THEN source_row.outcome
                            WHEN 4 THEN CASE
                                WHEN source_payloads_pass THEN '6-of-6'
                                ELSE 'fewer-than-6-passing'
                            END
                            WHEN 5 THEN CASE
                                WHEN source_checks_pass THEN '12-of-12'
                                ELSE 'fewer-than-12-passing'
                            END
                            WHEN 6 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                WHEN external_requests_complete
                                    THEN 'complete-read-only-evidence'
                                ELSE 'incomplete-or-unverified'
                            END
                            WHEN 7 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                ELSE 'unverified'
                            END
                            WHEN 8 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                WHEN source_rights_current THEN 'current-but-unverified'
                                ELSE 'missing-or-stale'
                            END
                            WHEN 9 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                WHEN source_rights_sufficient THEN 'sufficient-but-unverified'
                                ELSE 'missing-or-insufficient'
                            END
                            WHEN 10 THEN 'absent'
                            WHEN 11 THEN 'absent'
                            WHEN 12 THEN CASE
                                WHEN source_authority_absent THEN 'absent'
                                ELSE 'present'
                            END
                        END
                        OR policy_check.threshold_value IS DISTINCT FROM CASE policy_check.ordinal
                            WHEN 1 THEN 'valid'
                            WHEN 2 THEN 'DETERMINISTIC_MOCK'
                            WHEN 3 THEN 'MOCK_PROOF_COMPLETE'
                            WHEN 4 THEN '6-of-6'
                            WHEN 5 THEN '12-of-12'
                            WHEN 6 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                ELSE '5-of-5-observed'
                            END
                            WHEN 7 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                ELSE 'independently-authenticated'
                            END
                            WHEN 8 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                ELSE 'independently-verified-current'
                            END
                            WHEN 9 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN 'mock-not-applicable'
                                ELSE 'independently-verified-storage-nondisplay-derived'
                            END
                            WHEN 10 THEN 'absent'
                            WHEN 11 THEN 'absent'
                            WHEN 12 THEN 'absent'
                        END
                        OR policy_check.evidence_sha256s IS DISTINCT FROM CASE policy_check.ordinal
                            WHEN 1 THEN source_identity_evidence
                            WHEN 2 THEN source_artifact_request_evidence
                            WHEN 3 THEN jsonb_build_array(source_row.artifact_sha256)
                            WHEN 4 THEN source_capability_evidence
                            WHEN 5 THEN source_check_evidence
                            WHEN 6 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                    THEN source_artifact_capture_evidence
                                WHEN jsonb_array_length(source_request_evidence) > 0
                                    THEN source_request_evidence
                                ELSE jsonb_build_array(source_row.artifact_sha256)
                            END
                            WHEN 7 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     OR source_row.rights_attestation_sha256 IS NULL
                                    THEN jsonb_build_array(source_row.artifact_sha256)
                                ELSE jsonb_build_array(source_row.rights_attestation_sha256)
                            END
                            WHEN 8 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     OR source_row.rights_attestation_sha256 IS NULL
                                    THEN jsonb_build_array(source_row.artifact_sha256)
                                ELSE jsonb_build_array(source_row.rights_attestation_sha256)
                            END
                            WHEN 9 THEN CASE
                                WHEN source_row.source_kind = 'DETERMINISTIC_MOCK'
                                     OR source_row.rights_attestation_sha256 IS NULL
                                    THEN jsonb_build_array(source_row.artifact_sha256)
                                ELSE jsonb_build_array(source_row.rights_attestation_sha256)
                            END
                            WHEN 10 THEN source_artifact_payload_manifest_evidence
                            WHEN 11 THEN jsonb_build_array(source_row.artifact_sha256)
                            WHEN 12 THEN source_check_evidence
                        END
                      )
               )
               OR EXISTS (
                    SELECT 1
                    FROM research_ingestion_eligibility_checks
                    WHERE assessment_id = checked_assessment_id
                      AND ordinal BETWEEN 10 AND 12
                      AND (status <> 'PASS' OR reason_code <> 'check_passed')
               )
               OR (
                    run_row.qualification_source_kind = 'DETERMINISTIC_MOCK'
                    AND EXISTS (
                        SELECT 1
                        FROM research_ingestion_eligibility_checks
                        WHERE assessment_id = checked_assessment_id
                          AND ordinal BETWEEN 6 AND 9
                          AND (status <> 'PASS' OR reason_code <> 'mock_not_applicable')
                    )
               ) THEN
                RAISE EXCEPTION
                    'Phase 14 eligibility requires exact complete source-bound evidence';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        f"""
        CREATE FUNCTION reject_phase14_eligibility_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '{PHASE14_APPEND_ONLY_ERROR}';
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _install_validation_triggers() -> None:
    for table in PHASE14_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase14_created_at_utc()
            """
        )
    op.execute(
        """
        CREATE TRIGGER research_ingestion_eligibility_assessments_05_idempotency_lock
        BEFORE INSERT ON research_ingestion_eligibility_assessments
        FOR EACH ROW EXECUTE FUNCTION phase14_lock_eligibility_idempotency()
        """
    )
    for table, function_name in (
        (
            "research_ingestion_eligibility_assessments",
            "validate_phase14_eligibility_root_payload",
        ),
        (
            "research_ingestion_eligibility_payloads",
            "validate_phase14_eligibility_payload",
        ),
        (
            "research_ingestion_eligibility_checks",
            "validate_phase14_eligibility_check_payload",
        ),
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_10_payload
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION {function_name}()
            """
        )
    for table in PHASE14_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase14_eligibility_completeness()
            """
        )


def _install_append_only_guards() -> None:
    for table in PHASE14_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_90_append_only_row
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase14_eligibility_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_91_append_only_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase14_eligibility_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE14_TABLES):
        op.drop_table(table)
    for function_name in (
        "reject_phase14_eligibility_mutation()",
        "validate_phase14_eligibility_completeness()",
        "validate_phase14_eligibility_check_payload()",
        "validate_phase14_eligibility_payload()",
        "validate_phase14_eligibility_root_payload()",
        "phase14_lock_eligibility_idempotency()",
        "own_phase14_created_at_utc()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}")
