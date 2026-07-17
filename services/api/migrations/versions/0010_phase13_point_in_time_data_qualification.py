"""Add immutable Phase 13 point-in-time qualification evidence.

Revision ID: 0010_phase13
Revises: 0009_phase12

This revision owns sanitized provider-qualification evidence only. It adds no
research snapshot, strategy, performance, approval, risk, execution, order, or
live-trading capability.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_phase13"
down_revision: str | None = "0009_phase12"
branch_labels: str | None = None
depends_on: str | None = None

PHASE13_TABLES = (
    "point_in_time_qualification_runs",
    "point_in_time_qualification_payloads",
    "point_in_time_qualification_checks",
)

PHASE13_CAPABILITY_CODES = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)

PHASE13_CHECK_CODES = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "USE_RIGHTS_CURRENT_SUFFICIENT",
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
    "RAW_NORMALIZED_RECONCILIATION",
    "NULL_SENTINEL_SCHEMA_DRIFT",
    "DETERMINISTIC_CAPTURE_MANIFEST",
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

PHASE13_RUN_NAMESPACE = "298dd99c-ab11-5c8b-98aa-866ebbb91313"
PHASE13_APPEND_ONLY_ERROR = "Phase 13 point-in-time qualification artifacts are append-only"


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
        "point_in_time_qualification_runs",
        sa.Column("qualification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("qualification_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("provider_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_version", sa.String(length=256), nullable=False),
        sa.Column("dataset_id", sa.String(length=256), nullable=False),
        sa.Column("product_id", sa.String(length=256), nullable=False),
        sa.Column("provider_synthetic", sa.Boolean(), nullable=False),
        sa.Column("transport_profile_sha256", sa.String(length=64), nullable=False),
        sa.Column("rights_attestation_id", sa.String(length=256), nullable=True),
        sa.Column("rights_attestation_sha256", sa.String(length=64), nullable=True),
        sa.Column("rights_valid_from_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rights_expires_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rights_storage_allowed", sa.Boolean(), nullable=True),
        sa.Column("rights_non_display_allowed", sa.Boolean(), nullable=True),
        sa.Column("rights_derived_data_allowed", sa.Boolean(), nullable=True),
        sa.Column("sample_plan_id", sa.String(length=256), nullable=False),
        sa.Column("sample_plan_sha256", sa.String(length=64), nullable=False),
        sa.Column("capture_manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("research_data_eligible", sa.Boolean(), nullable=False),
        sa.Column("strategy_promotion_authorized", sa.Boolean(), nullable=False),
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
                "transport_profile_sha256",
                "sample_plan_sha256",
                "capture_manifest_sha256",
            ),
            name="ck_point_in_time_qualification_run_hashes",
        ),
        sa.CheckConstraint(
            "rights_attestation_sha256 IS NULL OR rights_attestation_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_point_in_time_qualification_rights_hash",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase13-pit-qualification-v1' "
            "AND qualification_idempotency_key "
            "    ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$' "
            "AND source_kind IN ('DETERMINISTIC_MOCK','TIINGO_CANDIDATE_READ_ONLY') "
            "AND outcome IN ('MOCK_PROOF_COMPLETE','EXTERNAL_SAMPLE_QUALIFIED','BLOCKED') "
            "AND provider_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND adapter_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND adapter_version ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND dataset_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND product_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND sample_plan_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "AND transport_profile_sha256 = "
            "'516141ae52eac2cbef09302f8f5928b9453ba227922f9e81e86c2449ea379109' "
            "AND sample_plan_id = 'phase13-family-a-qualification-sample-v1' "
            "AND sample_plan_sha256 = "
            "'32494657f8c71f7fa7c198ed4b70e9d1b8391b2c3b89963e6c67598b77256438' "
            "AND code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND started_at_utc <= completed_at_utc "
            "AND completed_at_utc <= created_at_utc "
            "AND NOT research_data_eligible "
            "AND NOT strategy_promotion_authorized "
            "AND NOT strategy_execution_eligible "
            "AND NOT execution_authorized "
            "AND NOT order_submission_authorized "
            "AND live_path_absent "
            "AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND NOT (source_kind = 'DETERMINISTIC_MOCK' "
            "         AND outcome = 'EXTERNAL_SAMPLE_QUALIFIED') "
            "AND NOT (source_kind = 'TIINGO_CANDIDATE_READ_ONLY' "
            "         AND outcome = 'MOCK_PROOF_COMPLETE') "
            "AND ((source_kind = 'DETERMINISTIC_MOCK' AND provider_synthetic "
            "      AND rights_attestation_id IS NULL "
            "      AND rights_attestation_sha256 IS NULL "
            "      AND rights_valid_from_utc IS NULL "
            "      AND rights_expires_at_utc IS NULL "
            "      AND rights_storage_allowed IS NULL "
            "      AND rights_non_display_allowed IS NULL "
            "      AND rights_derived_data_allowed IS NULL) "
            "  OR (source_kind = 'TIINGO_CANDIDATE_READ_ONLY' "
            "      AND NOT provider_synthetic "
            "      AND rights_attestation_id "
            "          ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$' "
            "      AND rights_attestation_sha256 IS NOT NULL "
            "      AND rights_valid_from_utc < rights_expires_at_utc)) "
            "AND (outcome <> 'EXTERNAL_SAMPLE_QUALIFIED' "
            "     OR (rights_valid_from_utc <= completed_at_utc "
            "         AND completed_at_utc < rights_expires_at_utc "
            "         AND rights_storage_allowed "
            "         AND rights_non_display_allowed "
            "         AND rights_derived_data_allowed)) "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_point_in_time_qualification_run_boundary",
        ),
        sa.PrimaryKeyConstraint("qualification_id", name="pk_point_in_time_qualification_runs"),
        sa.UniqueConstraint("artifact_sha256", name="uq_point_in_time_qualification_artifact"),
        sa.UniqueConstraint(
            "request_fingerprint_sha256",
            name="uq_point_in_time_qualification_request",
        ),
        sa.UniqueConstraint(
            "qualification_idempotency_key",
            name="uq_point_in_time_qualification_idempotency",
        ),
        sa.UniqueConstraint(
            "qualification_id",
            "artifact_sha256",
            name="uq_point_in_time_qualification_run_artifact",
        ),
    )

    op.create_table(
        "point_in_time_qualification_payloads",
        sa.Column("qualification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qualification_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=256), nullable=False),
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
        _json("request_evidence"),
        sa.Column("capability_manifest_sha256", sa.String(length=64), nullable=False),
        _json("payload"),
        _created_at(),
        _hash_check(
            (
                "qualification_artifact_sha256",
                "capability_manifest_sha256",
            ),
            name="ck_point_in_time_qualification_payload_hashes",
        ),
        sa.CheckConstraint(
            "(raw_evidence_sha256 IS NULL "
            " OR raw_evidence_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (normalized_evidence_sha256 IS NULL "
            " OR normalized_evidence_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (schema_identity_sha256 IS NULL "
            " OR schema_identity_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_point_in_time_qualification_payload_optional_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase13-pit-capability-manifest-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE13_CAPABILITY_CODES)} "
            f"AND capability IN ({_codes_sql(PHASE13_CAPABILITY_CODES)}) "
            "AND status IN ('PASS','BLOCKED','UNCOMPUTABLE') "
            f"AND reason_code IN ({_codes_sql(PHASE13_REASON_CODES)}) "
            "AND record_count >= 0 AND missingness_count >= 0 "
            "AND revision_count >= 0 "
            "AND ((event_time_min_utc IS NULL AND event_time_max_utc IS NULL) "
            "     OR (event_time_min_utc IS NOT NULL AND event_time_max_utc IS NOT NULL "
            "         AND event_time_min_utc <= event_time_max_utc)) "
            "AND ((available_at_min_utc IS NULL AND available_at_max_utc IS NULL) "
            "     OR (available_at_min_utc IS NOT NULL "
            "         AND available_at_max_utc IS NOT NULL "
            "         AND available_at_min_utc <= available_at_max_utc "
            "         AND available_at_max_utc <= decision_time_utc)) "
            "AND ((status = 'PASS' AND reason_code = 'check_passed' "
            "      AND record_count >= 1 "
            "      AND raw_evidence_sha256 IS NOT NULL "
            "      AND normalized_evidence_sha256 IS NOT NULL "
            "      AND schema_identity_sha256 IS NOT NULL) "
            "  OR (status <> 'PASS' AND reason_code <> 'check_passed')) "
            "AND jsonb_typeof(request_evidence) = 'array' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_point_in_time_qualification_payload_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["qualification_id", "qualification_artifact_sha256"],
            [
                "point_in_time_qualification_runs.qualification_id",
                "point_in_time_qualification_runs.artifact_sha256",
            ],
            name="fk_point_in_time_qualification_payload_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "qualification_id",
            "ordinal",
            name="pk_point_in_time_qualification_payloads",
        ),
        sa.UniqueConstraint(
            "qualification_id",
            "capability",
            name="uq_point_in_time_qualification_payload_capability",
        ),
        sa.UniqueConstraint(
            "qualification_id",
            "capability_manifest_sha256",
            name="uq_point_in_time_qualification_payload_hash",
        ),
    )

    op.create_table(
        "point_in_time_qualification_checks",
        sa.Column("qualification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qualification_artifact_sha256", sa.String(length=64), nullable=False),
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
            ("qualification_artifact_sha256", "check_sha256"),
            name="ck_point_in_time_qualification_check_hashes",
        ),
        sa.CheckConstraint(
            f"schema_version = 'phase13-pit-qualification-check-v1' "
            f"AND ordinal BETWEEN 1 AND {len(PHASE13_CHECK_CODES)} "
            f"AND code IN ({_codes_sql(PHASE13_CHECK_CODES)}) "
            "AND status IN ('PASS','BLOCKED','UNCOMPUTABLE') "
            f"AND reason_code IN ({_codes_sql(PHASE13_REASON_CODES)}) "
            "AND ((status = 'PASS' AND reason_code IN "
            "      ('check_passed','mock_rights_not_applicable')) "
            "  OR (status <> 'PASS' AND reason_code NOT IN "
            "      ('check_passed','mock_rights_not_applicable'))) "
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
            name="ck_point_in_time_qualification_check_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["qualification_id", "qualification_artifact_sha256"],
            [
                "point_in_time_qualification_runs.qualification_id",
                "point_in_time_qualification_runs.artifact_sha256",
            ],
            name="fk_point_in_time_qualification_check_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "qualification_id",
            "ordinal",
            name="pk_point_in_time_qualification_checks",
        ),
        sa.UniqueConstraint(
            "qualification_id",
            "code",
            name="uq_point_in_time_qualification_check_code",
        ),
        sa.UniqueConstraint(
            "qualification_id",
            "check_sha256",
            name="uq_point_in_time_qualification_check_hash",
        ),
    )

    _install_validation_functions()
    _install_validation_triggers()
    _install_append_only_guards()


def _install_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION own_phase13_created_at_utc()
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
        CREATE FUNCTION phase13_lock_qualification_idempotency()
        RETURNS trigger AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(
                hashtextextended(
                    'phase13-qualification-workflow:'
                        || NEW.qualification_idempotency_key,
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
        CREATE FUNCTION validate_phase13_qualification_root_payload()
        RETURNS trigger AS $$
        DECLARE
            body jsonb;
            profile jsonb;
            rights jsonb;
            expected_request text;
            expected_artifact text;
        BEGIN
            body := NEW.artifact_payload;
            profile := body->'provider_profile';
            rights := body->'rights_attestation';
            expected_request := phase6_domain_sha256(
                'phase13-pit-qualification-request-v1',
                jsonb_build_object(
                    'schema_version', NEW.schema_version,
                    'qualification_idempotency_key',
                        NEW.qualification_idempotency_key,
                    'source_kind', NEW.source_kind,
                    'provider_profile', profile,
                    'sample_plan_id', NEW.sample_plan_id,
                    'sample_plan_sha256', NEW.sample_plan_sha256,
                    'transport_profile_sha256', NEW.transport_profile_sha256,
                    'code_version_git_sha', NEW.code_version_git_sha
                )
            );
            expected_artifact := phase6_domain_sha256(
                'phase13-pit-qualification-artifact-v1', body
            );
            IF (SELECT count(*) FROM jsonb_object_keys(body)) <> 26
               OR NOT body ?& ARRAY[
                    'schema_version','qualification_id',
                    'qualification_idempotency_key','request_fingerprint_sha256',
                    'source_kind','outcome','provider_profile','rights_attestation',
                    'sample_plan_id','sample_plan_sha256',
                    'transport_profile_sha256','capture_manifest_sha256',
                    'started_at_utc','completed_at_utc','code_version_git_sha',
                    'capability_manifests','checks','research_data_eligible',
                    'strategy_promotion_authorized','strategy_execution_eligible',
                    'execution_authorized','order_submission_authorized',
                    'live_path_absent','no_personalized_investment_advice',
                    'no_real_performance_claimed','disclaimer'
               ]
               OR body->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (body->>'qualification_id')::uuid
                    IS DISTINCT FROM NEW.qualification_id
               OR body->>'qualification_idempotency_key'
                    IS DISTINCT FROM NEW.qualification_idempotency_key
               OR body->>'request_fingerprint_sha256'
                    IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR body->>'source_kind' IS DISTINCT FROM NEW.source_kind
               OR body->>'outcome' IS DISTINCT FROM NEW.outcome
               OR body->>'sample_plan_id' IS DISTINCT FROM NEW.sample_plan_id
               OR body->>'sample_plan_sha256' IS DISTINCT FROM NEW.sample_plan_sha256
               OR body->>'transport_profile_sha256'
                    IS DISTINCT FROM NEW.transport_profile_sha256
               OR body->>'capture_manifest_sha256'
                    IS DISTINCT FROM NEW.capture_manifest_sha256
               OR (body->>'started_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.started_at_utc
               OR (body->>'completed_at_utc')::timestamptz
                    IS DISTINCT FROM NEW.completed_at_utc
               OR body->>'code_version_git_sha'
                    IS DISTINCT FROM NEW.code_version_git_sha
               OR (body->>'research_data_eligible')::boolean
                    IS DISTINCT FROM NEW.research_data_eligible
               OR (body->>'strategy_promotion_authorized')::boolean
                    IS DISTINCT FROM NEW.strategy_promotion_authorized
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
                    'Qualification-only sample evidence; not a research dataset, strategy '
                    'result, execution authority, performance claim, or personalized '
                    'investment advice.'
               OR jsonb_typeof(body->'capability_manifests') <> 'array'
               OR jsonb_typeof(body->'checks') <> 'array'
               OR jsonb_typeof(profile) <> 'object'
               OR (SELECT count(*) FROM jsonb_object_keys(profile)) <> 9
               OR profile->>'schema_version'
                    IS DISTINCT FROM 'phase13-pit-provider-profile-v1'
               OR profile->>'source_kind' IS DISTINCT FROM NEW.source_kind
               OR profile->>'provider_id' IS DISTINCT FROM NEW.provider_id
               OR profile->>'adapter_id' IS DISTINCT FROM NEW.adapter_id
               OR profile->>'adapter_version' IS DISTINCT FROM NEW.adapter_version
               OR profile->>'dataset_id' IS DISTINCT FROM NEW.dataset_id
               OR profile->>'product_id' IS DISTINCT FROM NEW.product_id
               OR (profile->>'synthetic')::boolean
                    IS DISTINCT FROM NEW.provider_synthetic
               OR profile->>'transport_profile_sha256'
                    IS DISTINCT FROM NEW.transport_profile_sha256
               OR (
                    NEW.source_kind = 'DETERMINISTIC_MOCK'
                    AND rights IS DISTINCT FROM 'null'::jsonb
               )
               OR (
                    NEW.source_kind = 'TIINGO_CANDIDATE_READ_ONLY'
                    AND (
                        jsonb_typeof(rights) <> 'object'
                        OR (SELECT count(*) FROM jsonb_object_keys(rights)) <> 9
                        OR rights->>'schema_version'
                            IS DISTINCT FROM 'phase13-pit-rights-attestation-v1'
                        OR rights->>'attestation_id'
                            IS DISTINCT FROM NEW.rights_attestation_id
                        OR rights->>'attestation_sha256'
                            IS DISTINCT FROM NEW.rights_attestation_sha256
                        OR (rights->>'valid_from_utc')::timestamptz
                            IS DISTINCT FROM NEW.rights_valid_from_utc
                        OR (rights->>'expires_at_utc')::timestamptz
                            IS DISTINCT FROM NEW.rights_expires_at_utc
                        OR (rights->>'storage_allowed')::boolean
                            IS DISTINCT FROM NEW.rights_storage_allowed
                        OR (rights->>'non_display_allowed')::boolean
                            IS DISTINCT FROM NEW.rights_non_display_allowed
                        OR (rights->>'derived_data_allowed')::boolean
                            IS DISTINCT FROM NEW.rights_derived_data_allowed
                        OR (rights->>'qualification_use_only')::boolean
                            IS DISTINCT FROM TRUE
                    )
               )
               OR expected_request IS DISTINCT FROM NEW.request_fingerprint_sha256
               OR phase6_uuid5(
                    '{PHASE13_RUN_NAMESPACE}'::uuid, expected_request
                  ) IS DISTINCT FROM NEW.qualification_id
               OR expected_artifact IS DISTINCT FROM NEW.artifact_sha256 THEN
                RAISE EXCEPTION 'Phase 13 qualification root payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase13_qualification_payload_manifest()
        RETURNS trigger AS $$
        DECLARE
            request_item jsonb;
            request_ordinals integer[];
        BEGIN
            IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 18
               OR NOT NEW.payload ?& ARRAY[
                    'schema_version','ordinal','capability','status','reason_code',
                    'decision_time_utc','event_time_min_utc','event_time_max_utc',
                    'available_at_min_utc','available_at_max_utc','record_count',
                    'missingness_count','revision_count','raw_evidence_sha256',
                    'normalized_evidence_sha256','schema_identity_sha256',
                    'request_evidence','capability_manifest_sha256'
               ]
               OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
               OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
               OR NEW.payload->>'capability' IS DISTINCT FROM NEW.capability
               OR NEW.payload->>'status' IS DISTINCT FROM NEW.status
               OR NEW.payload->>'reason_code' IS DISTINCT FROM NEW.reason_code
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
               OR (NEW.payload->>'record_count')::integer
                    IS DISTINCT FROM NEW.record_count
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
               OR NEW.payload->'request_evidence' IS DISTINCT FROM NEW.request_evidence
               OR NEW.payload->>'capability_manifest_sha256'
                    IS DISTINCT FROM NEW.capability_manifest_sha256
               OR phase6_domain_sha256(
                    'phase13-pit-capability-manifest-v1',
                    NEW.payload - 'capability_manifest_sha256'
                  ) IS DISTINCT FROM NEW.capability_manifest_sha256 THEN
                RAISE EXCEPTION 'Phase 13 capability manifest payload mismatch';
            END IF;

            SELECT array_agg((item->>'ordinal')::integer ORDER BY position)
            INTO request_ordinals
            FROM jsonb_array_elements(NEW.request_evidence)
                WITH ORDINALITY AS request(item, position);
            IF request_ordinals IS NOT NULL AND request_ordinals IS DISTINCT FROM (
                    SELECT array_agg(value ORDER BY value)
                    FROM (SELECT DISTINCT unnest(request_ordinals) AS value) AS distinct_values
               ) THEN
                RAISE EXCEPTION 'Phase 13 request evidence order is not canonical';
            END IF;

            FOR request_item IN SELECT value FROM jsonb_array_elements(NEW.request_evidence)
            LOOP
                IF jsonb_typeof(request_item) <> 'object'
                   OR (SELECT count(*) FROM jsonb_object_keys(request_item)) <> 17
                   OR NOT request_item ?& ARRAY[
                        'schema_version','ordinal','code','status','method','host',
                        'port','target','external_request_performed',
                        'request_started_at_utc','request_completed_at_utc',
                        'http_status','raw_body_sha256','body_size_bytes',
                        'record_count','reason_code','request_evidence_sha256'
                   ]
                   OR request_item->>'schema_version'
                        IS DISTINCT FROM 'phase13-pit-request-evidence-v1'
                   OR request_item->>'ordinal' IS NULL
                   OR request_item->>'code' IS NULL
                   OR request_item->>'status' IS NULL
                   OR request_item->>'method' IS NULL
                   OR request_item->>'host' IS NULL
                   OR request_item->>'port' IS NULL
                   OR request_item->>'target' IS NULL
                   OR request_item->>'external_request_performed' IS NULL
                   OR request_item->>'reason_code' IS NULL
                   OR (request_item->>'ordinal')::integer NOT BETWEEN 1 AND 5
                   OR request_item->>'code' NOT IN (
                        'FUNDAMENTALS_META','EOD_PRICES','DISTRIBUTIONS',
                        'SPLITS','FUNDAMENTAL_STATEMENTS'
                   )
                   OR request_item->>'status' NOT IN (
                        'OBSERVED','BLOCKED','NOT_ATTEMPTED'
                   )
                   OR request_item->>'method' IS DISTINCT FROM 'GET'
                   OR request_item->>'host' IS DISTINCT FROM 'api.tiingo.com'
                   OR (request_item->>'port')::integer IS DISTINCT FROM 443
                   OR request_item->>'target' NOT IN (
                        '/tiingo/fundamentals/meta?columns=permaTicker,ticker,'
                            'isActive,statementLastUpdated,dailyLastUpdated',
                        '/tiingo/daily/AAPL/prices?startDate=2020-08-28&'
                            'endDate=2020-09-01',
                        '/tiingo/corporate-actions/AAPL/distributions?'
                            'startExDate=2020-01-01&endExDate=2020-12-31',
                        '/tiingo/corporate-actions/AAPL/splits?'
                            'startExDate=2020-08-28&endExDate=2020-09-01',
                        '/tiingo/fundamentals/AAPL/statements?startDate=2019-01-01'
                   )
                   OR (
                        (request_item->>'ordinal')::integer = 1
                        AND (
                            request_item->>'code' IS DISTINCT FROM 'FUNDAMENTALS_META'
                            OR request_item->>'target' IS DISTINCT FROM
                                '/tiingo/fundamentals/meta?columns=permaTicker,'
                                'ticker,isActive,statementLastUpdated,dailyLastUpdated'
                            OR NEW.capability IS DISTINCT FROM
                                'SECURITY_MASTER_STABLE_IDENTITY'
                        )
                   )
                   OR (
                        (request_item->>'ordinal')::integer = 2
                        AND (
                            request_item->>'code' IS DISTINCT FROM 'EOD_PRICES'
                            OR request_item->>'target' IS DISTINCT FROM
                                '/tiingo/daily/AAPL/prices?startDate=2020-08-28&'
                                'endDate=2020-09-01'
                            OR NEW.capability IS DISTINCT FROM 'RAW_OHLCV_AVAILABILITY'
                        )
                   )
                   OR (
                        (request_item->>'ordinal')::integer = 3
                        AND (
                            request_item->>'code' IS DISTINCT FROM 'DISTRIBUTIONS'
                            OR request_item->>'target' IS DISTINCT FROM
                                '/tiingo/corporate-actions/AAPL/distributions?'
                                'startExDate=2020-01-01&endExDate=2020-12-31'
                            OR NEW.capability IS DISTINCT FROM
                                'CORPORATE_ACTION_ANNOUNCEMENT_REVISION'
                        )
                   )
                   OR (
                        (request_item->>'ordinal')::integer = 4
                        AND (
                            request_item->>'code' IS DISTINCT FROM 'SPLITS'
                            OR request_item->>'target' IS DISTINCT FROM
                                '/tiingo/corporate-actions/AAPL/splits?'
                                'startExDate=2020-08-28&endExDate=2020-09-01'
                            OR NEW.capability IS DISTINCT FROM
                                'CORPORATE_ACTION_ANNOUNCEMENT_REVISION'
                        )
                   )
                   OR (
                        (request_item->>'ordinal')::integer = 5
                        AND (
                            request_item->>'code' IS DISTINCT FROM
                                'FUNDAMENTAL_STATEMENTS'
                            OR request_item->>'target' IS DISTINCT FROM
                                '/tiingo/fundamentals/AAPL/statements?startDate=2019-01-01'
                            OR NEW.capability IS DISTINCT FROM
                                'AS_REPORTED_FUNDAMENTAL_REVISION'
                        )
                   )
                   OR request_item->>'reason_code' NOT IN (
                        {_codes_sql(PHASE13_REASON_CODES)}
                   )
                   OR (request_item->>'external_request_performed')::boolean IS NULL
                   OR (
                        request_item->>'http_status' IS NOT NULL
                        AND (request_item->>'http_status')::integer NOT BETWEEN 100 AND 599
                   )
                   OR (
                        request_item->>'raw_body_sha256' IS NOT NULL
                        AND request_item->>'raw_body_sha256' !~ '^[0-9a-f]{{64}}$'
                   )
                   OR (
                        request_item->>'body_size_bytes' IS NOT NULL
                        AND (request_item->>'body_size_bytes')::integer NOT BETWEEN 1 AND 2000000
                   )
                   OR (
                        request_item->>'record_count' IS NOT NULL
                        AND (request_item->>'record_count')::integer NOT BETWEEN 0 AND 100000
                   )
                   OR (
                        (request_item->>'request_started_at_utc' IS NULL)
                        <> (request_item->>'request_completed_at_utc' IS NULL)
                   )
                   OR (
                        request_item->>'request_started_at_utc' IS NOT NULL
                        AND (request_item->>'request_started_at_utc')::timestamptz
                            > (request_item->>'request_completed_at_utc')::timestamptz
                   )
                   OR (
                        request_item->>'status' = 'OBSERVED'
                        AND (
                            request_item->>'request_started_at_utc' IS NULL
                            OR request_item->>'raw_body_sha256' IS NULL
                            OR request_item->>'body_size_bytes' IS NULL
                            OR request_item->>'record_count' IS NULL
                            OR request_item->>'reason_code' <> 'check_passed'
                            OR (
                                (request_item->>'external_request_performed')::boolean
                                AND (request_item->>'http_status')::integer IS DISTINCT FROM 200
                            )
                            OR (
                                NOT (request_item->>'external_request_performed')::boolean
                                AND request_item->>'http_status' IS NOT NULL
                            )
                        )
                   )
                   OR (
                        request_item->>'status' = 'NOT_ATTEMPTED'
                        AND (
                            request_item->>'request_started_at_utc' IS NOT NULL
                            OR (request_item->>'external_request_performed')::boolean
                            OR request_item->>'http_status' IS NOT NULL
                            OR request_item->>'raw_body_sha256' IS NOT NULL
                            OR request_item->>'body_size_bytes' IS NOT NULL
                            OR request_item->>'record_count' IS NOT NULL
                            OR request_item->>'reason_code' = 'check_passed'
                        )
                   )
                   OR (
                        request_item->>'status' = 'BLOCKED'
                        AND (
                            request_item->>'request_started_at_utc' IS NULL
                            OR request_item->>'reason_code' = 'check_passed'
                            OR (
                                NOT (request_item->>'external_request_performed')::boolean
                                AND request_item->>'http_status' IS NOT NULL
                            )
                        )
                   )
                   OR request_item->>'request_evidence_sha256'
                        !~ '^[0-9a-f]{{64}}$'
                   OR phase6_domain_sha256(
                        'phase13-pit-request-evidence-v1',
                        request_item - 'request_evidence_sha256'
                      ) IS DISTINCT FROM request_item->>'request_evidence_sha256' THEN
                    RAISE EXCEPTION 'Phase 13 request evidence payload mismatch';
                END IF;
            END LOOP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase13_qualification_check_payload()
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
               OR phase6_domain_sha256(
                    'phase13-pit-qualification-check-v1',
                    NEW.payload - 'check_sha256'
                  ) IS DISTINCT FROM NEW.check_sha256 THEN
                RAISE EXCEPTION 'Phase 13 qualification check payload mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase13_qualification_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_qualification_id uuid;
            run_row point_in_time_qualification_runs%ROWTYPE;
            payload_count bigint;
            payload_minimum_ordinal integer;
            payload_maximum_ordinal integer;
            actual_capabilities jsonb;
            actual_payloads jsonb;
            payloads_pass boolean;
            check_count bigint;
            check_minimum_ordinal integer;
            check_maximum_ordinal integer;
            actual_codes jsonb;
            actual_checks jsonb;
            checks_pass boolean;
            expected_capture text;
            expected_outcome text;
            external_request_codes jsonb;
        BEGIN
            checked_qualification_id := NEW.qualification_id;
            SELECT * INTO run_row
            FROM point_in_time_qualification_runs
            WHERE qualification_id = checked_qualification_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 13 qualification completeness target is missing';
            END IF;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(capability) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO payload_count, payload_minimum_ordinal, payload_maximum_ordinal,
                 actual_capabilities, actual_payloads, payloads_pass
            FROM point_in_time_qualification_payloads
            WHERE qualification_id = checked_qualification_id;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(bool_and(status = 'PASS'), false)
            INTO check_count, check_minimum_ordinal, check_maximum_ordinal,
                 actual_codes, actual_checks, checks_pass
            FROM point_in_time_qualification_checks
            WHERE qualification_id = checked_qualification_id;

            expected_capture := phase6_domain_sha256(
                'phase13-pit-capture-manifest-v1',
                jsonb_build_object(
                    'provider_profile', run_row.artifact_payload->'provider_profile',
                    'rights_attestation', run_row.artifact_payload->'rights_attestation',
                    'sample_plan_id', run_row.sample_plan_id,
                    'sample_plan_sha256', run_row.sample_plan_sha256,
                    'capability_manifest_sha256s',
                        COALESCE(
                            (
                                SELECT jsonb_agg(
                                    to_jsonb(capability_manifest_sha256)
                                    ORDER BY ordinal
                                )
                                FROM point_in_time_qualification_payloads
                                WHERE qualification_id = checked_qualification_id
                            ),
                            '[]'::jsonb
                        )
                )
            );
            expected_outcome := CASE
                WHEN NOT (payloads_pass AND checks_pass) THEN 'BLOCKED'
                WHEN run_row.source_kind = 'DETERMINISTIC_MOCK'
                    THEN 'MOCK_PROOF_COMPLETE'
                ELSE 'EXTERNAL_SAMPLE_QUALIFIED'
            END;

            SELECT COALESCE(
                jsonb_agg(DISTINCT request_item->'code' ORDER BY request_item->'code'),
                '[]'::jsonb
            ) INTO external_request_codes
            FROM point_in_time_qualification_payloads AS manifest
            CROSS JOIN LATERAL jsonb_array_elements(manifest.request_evidence)
                AS request(request_item)
            WHERE manifest.qualification_id = checked_qualification_id
              AND (request_item->>'external_request_performed')::boolean
              AND request_item->>'status' = 'OBSERVED';

            IF payload_count <> {len(PHASE13_CAPABILITY_CODES)}
               OR payload_minimum_ordinal <> 1
               OR payload_maximum_ordinal <> {len(PHASE13_CAPABILITY_CODES)}
               OR actual_capabilities IS DISTINCT FROM
                    {_registry_json_sql(PHASE13_CAPABILITY_CODES)}
               OR actual_payloads IS DISTINCT FROM
                    run_row.artifact_payload->'capability_manifests'
               OR check_count <> {len(PHASE13_CHECK_CODES)}
               OR check_minimum_ordinal <> 1
               OR check_maximum_ordinal <> {len(PHASE13_CHECK_CODES)}
               OR actual_codes IS DISTINCT FROM {_registry_json_sql(PHASE13_CHECK_CODES)}
               OR actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'
               OR expected_capture IS DISTINCT FROM run_row.capture_manifest_sha256
               OR expected_outcome IS DISTINCT FROM run_row.outcome
               OR (
                    run_row.source_kind = 'DETERMINISTIC_MOCK'
                    AND external_request_codes <> '[]'::jsonb
               )
               OR (
                    run_row.outcome = 'EXTERNAL_SAMPLE_QUALIFIED'
                    AND external_request_codes IS DISTINCT FROM
                        '["DISTRIBUTIONS","EOD_PRICES","FUNDAMENTALS_META",'
                        '"FUNDAMENTAL_STATEMENTS","SPLITS"]'::jsonb
               ) THEN
                RAISE EXCEPTION
                    'Phase 13 qualification requires exact complete ordered evidence';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _install_validation_triggers() -> None:
    for table in PHASE13_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase13_created_at_utc()
            """
        )
    op.execute(
        """
        CREATE TRIGGER point_in_time_qualification_runs_05_idempotency_lock
        BEFORE INSERT ON point_in_time_qualification_runs
        FOR EACH ROW EXECUTE FUNCTION phase13_lock_qualification_idempotency()
        """
    )
    for table, function_name in (
        (
            "point_in_time_qualification_runs",
            "validate_phase13_qualification_root_payload",
        ),
        (
            "point_in_time_qualification_payloads",
            "validate_phase13_qualification_payload_manifest",
        ),
        (
            "point_in_time_qualification_checks",
            "validate_phase13_qualification_check_payload",
        ),
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_10_payload
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION {function_name}()
            """
        )
    for table in PHASE13_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase13_qualification_completeness()
            """
        )


def _install_append_only_guards() -> None:
    op.execute(
        f"""
        CREATE FUNCTION reject_phase13_qualification_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '{PHASE13_APPEND_ONLY_ERROR}';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE13_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_90_append_only_row
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase13_qualification_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_91_append_only_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase13_qualification_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE13_TABLES):
        op.drop_table(table)
    for function_name in (
        "reject_phase13_qualification_mutation()",
        "validate_phase13_qualification_completeness()",
        "validate_phase13_qualification_check_payload()",
        "validate_phase13_qualification_payload_manifest()",
        "validate_phase13_qualification_root_payload()",
        "phase13_lock_qualification_idempotency()",
        "own_phase13_created_at_utc()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}")
