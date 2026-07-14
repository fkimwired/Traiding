"""Add Phase 6 research-only pipeline artifacts.

Revision ID: 0006_phase6
Revises: 0005_phase5
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase6"
down_revision: str | None = "0005_phase5"
branch_labels: str | None = None
depends_on: str | None = None


PHASE6_TABLES = (
    "research_pipeline_runs",
    "research_pipeline_snapshot_bindings",
    "research_pipeline_attempts",
    "research_feature_rows",
    "research_score_outputs",
    "research_baseline_comparisons",
    "research_text_extractions",
    "research_text_corroborations",
)

PHASE6_CHILD_TABLES = PHASE6_TABLES[1:]


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


def _phase4_snapshot_frozen_versions_constraint(*, extended: bool) -> str:
    fixture_constraint = (
        "fixture_set_version IN ("
        "'phase4-synthetic-pit-fixtures-v1',"
        "'phase6-synthetic-pit-fixtures-v1',"
        "'phase6-synthetic-pit-fixtures-v2')"
        if extended
        else "fixture_set_version = 'phase4-synthetic-pit-fixtures-v1'"
    )
    return (
        "request_fingerprint_version = 'phase4-request-fingerprint-v1' "
        "AND snapshot_schema_version = 'phase4-data-snapshot-v1' "
        "AND canonicalization_version = 'phase4-canonical-json-v1' "
        "AND date_only_availability_convention = "
        "'phase4-date-only-next-day-v1' "
        f"AND {fixture_constraint}"
    )


def _phase4_snapshot_capability_constraint(*, extended: bool) -> str:
    capabilities = (
        "'security_master','universe_membership','ohlcv','corporate_actions',"
        "'delistings','as_reported_fundamentals','trading_calendar',"
        "'volatility_return_inputs','official_document_event_metadata'"
    )
    if extended:
        capabilities += ",'macro_regime_inputs'"
    return f"capability IN ({capabilities})"


def _phase4_quality_finding_identity_constraint(*, extended: bool) -> str:
    rule_set_constraint = (
        "rule_set_version IN ("
        "'phase4-data-quality-v1',"
        "'phase6-data-contract-quality-v1',"
        "'phase6-data-contract-quality-v2')"
        if extended
        else "rule_set_version = 'phase4-data-quality-v1'"
    )
    return (
        f"{rule_set_constraint} "
        "AND btrim(rule_id) <> '' "
        "AND (affected_record_identity IS NULL "
        "OR btrim(affected_record_identity) <> '') "
        "AND (field_name IS NULL OR btrim(field_name) <> '')"
    )


def _phase4_quality_finding_code_constraint(*, extended: bool) -> str:
    phase6_codes = (
        ",'pit_classification_invalid'"
        ",'document_content_hash_mismatch'"
        ",'document_correction_timing_invalid'"
        ",'official_corroboration_mismatch'"
        if extended
        else ""
    )
    return (
        "code IN ("
        "'synthetic_fixture','date_only_convention_applied',"
        "'future_availability_excluded','near_duplicate_retained',"
        "'exact_duplicate_key','required_field_missing','invalid_enum_value',"
        "'invalid_timestamp_order','orphan_reference',"
        "'raw_normalized_lineage_gap',"
        "'unit_currency_calendar_timezone_mismatch','schema_drift',"
        "'current_universe_leakage','restatement_leakage',"
        "'corporate_action_lookahead','missing_delisting_return',"
        "'future_availability_included','unnormalized_rejected'"
        f"{phase6_codes})"
    )


def _phase4_record_type_function(*, extended: bool) -> str:
    sector_type = ", 'sector_classification'" if extended else ""
    official_condition = (
        "checked_record_type IN (\n"
        "                        'official_document_event', "
        "'official_document_content', 'social_attention'\n"
        "                    )"
        if extended
        else "checked_record_type = 'official_document_event'"
    )
    macro_branch = (
        "\n                WHEN 'macro_regime_inputs' THEN checked_record_type IN ("
        "'macro_rate_observation', 'crisis_window_definition')"
        if extended
        else ""
    )
    return f"""
        CREATE OR REPLACE FUNCTION phase4_record_type_matches_capability(
            checked_record_type text,
            checked_capability text
        ) RETURNS boolean AS $$
            SELECT CASE checked_capability
                WHEN 'security_master' THEN checked_record_type IN (
                    'instrument_identity', 'listing_identity'{sector_type}
                )
                WHEN 'universe_membership' THEN
                    checked_record_type = 'universe_membership'
                WHEN 'ohlcv' THEN checked_record_type = 'ohlcv_bar'
                WHEN 'corporate_actions' THEN checked_record_type = 'corporate_action'
                WHEN 'delistings' THEN checked_record_type = 'delisting_event'
                WHEN 'as_reported_fundamentals' THEN
                    checked_record_type = 'as_reported_fundamental'
                WHEN 'trading_calendar' THEN checked_record_type = 'calendar_session'
                WHEN 'volatility_return_inputs' THEN
                    checked_record_type = 'volatility_return_input'
                WHEN 'official_document_event_metadata' THEN
                    {official_condition}{macro_branch}
                ELSE false
            END
        $$ LANGUAGE sql IMMUTABLE
    """


def _phase4_snapshot_request_function(*, extended: bool) -> str:
    family_a_extra = "                    'macro_regime_inputs',\n" if extended else ""
    family_b_extra = (
        "'security_master','universe_membership',\n                    " if extended else ""
    )
    family_c_condition = (
        "NEW.capability NOT IN ("
        "'security_master','universe_membership','ohlcv',"
        "'official_document_event_metadata')"
        if extended
        else "NEW.capability <> 'official_document_event_metadata'"
    )
    vocabulary_extra = ",\n                    'macro_regime_inputs'" if extended else ""
    return f"""
        CREATE OR REPLACE FUNCTION validate_phase4_snapshot_request()
        RETURNS trigger AS $$
        DECLARE
            mapping record;
            expected_corroborations jsonb;
            expected_mapping jsonb;
            expected_rights jsonb;
            sorted_capabilities jsonb;
            sorted_schema_bindings jsonb;
        BEGIN
            SELECT
                version_number AS mapping_version,
                mapping_input_sha256,
                mapper_rule_set_version,
                mapper_rule_set_sha256,
                canonical_family,
                research_verdict AS verdict
            INTO mapping
            FROM research_mapping_versions
            WHERE id = NEW.mapping_id
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 mapping was not found';
            END IF;

            SELECT COALESCE(
                jsonb_agg(
                    official_source_version_id::text
                    ORDER BY official_source_version_id::text
                ),
                '[]'::jsonb
            ) INTO expected_corroborations
            FROM mapping_official_corroborations
            WHERE mapping_id = NEW.mapping_id;

            IF NEW.mapping_version IS DISTINCT FROM mapping.mapping_version
                OR NEW.mapping_input_sha256 IS DISTINCT FROM mapping.mapping_input_sha256
                OR NEW.mapper_rule_set_version
                    IS DISTINCT FROM mapping.mapper_rule_set_version
                OR NEW.mapper_rule_set_sha256
                    IS DISTINCT FROM mapping.mapper_rule_set_sha256
                OR NEW.canonical_family IS DISTINCT FROM mapping.canonical_family
                OR NEW.verdict IS DISTINCT FROM mapping.verdict
                OR NEW.official_corroboration_source_version_ids
                    IS DISTINCT FROM expected_corroborations THEN
                RAISE EXCEPTION 'Phase 4 persisted mapping lineage mismatch';
            END IF;
            IF mapping.verdict <> 'BUILD_RESEARCH' THEN
                RAISE EXCEPTION 'Phase 4 requires a BUILD_RESEARCH mapping';
            END IF;

            IF mapping.canonical_family = 'A_CROSS_SECTIONAL_EQUITY_RANKING' THEN
                IF NEW.capability NOT IN (
{family_a_extra}                    'security_master',
                    'universe_membership',
                    'ohlcv',
                    'corporate_actions',
                    'delistings',
                    'as_reported_fundamentals'
                ) THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family A';
                END IF;
            ELSIF mapping.canonical_family = 'B_TIME_SERIES_MOMENTUM_REGIME' THEN
                IF NEW.capability NOT IN (
                    {family_b_extra}'ohlcv',
                    'corporate_actions',
                    'delistings',
                    'trading_calendar',
                    'volatility_return_inputs'
                ) THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family B';
                END IF;
            ELSIF mapping.canonical_family = 'C_OFFICIAL_EVENT_TEXT_OVERLAY' THEN
                IF {family_c_condition} THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family C';
                END IF;
                IF jsonb_array_length(expected_corroborations) = 0 THEN
                    RAISE EXCEPTION 'Phase 4 Family C requires official corroboration';
                END IF;
            ELSE
                RAISE EXCEPTION 'Phase 4 mapping family is not authorized';
            END IF;

            SELECT COALESCE(jsonb_agg(value ORDER BY value), '[]'::jsonb)
            INTO sorted_capabilities
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements_text(NEW.capabilities)
            ) AS values;
            IF NEW.capabilities IS DISTINCT FROM sorted_capabilities
                OR NEW.capability NOT IN (
                    SELECT value FROM jsonb_array_elements_text(NEW.capabilities)
                ) THEN
                RAISE EXCEPTION 'Phase 4 adapter capabilities must be sorted and authoritative';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(NEW.capabilities) AS item(value)
                WHERE value NOT IN (
                    'security_master','universe_membership','ohlcv','corporate_actions',
                    'delistings','as_reported_fundamentals','trading_calendar',
                    'volatility_return_inputs','official_document_event_metadata'{vocabulary_extra}
                )
            ) THEN
                RAISE EXCEPTION 'Phase 4 adapter capability vocabulary is closed';
            END IF;

            IF EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.schema_bindings) AS item(value)
                WHERE jsonb_typeof(value) <> 'object'
                   OR btrim(value->>'dataset_schema_id') = ''
                   OR btrim(value->>'dataset_schema_version') = ''
            ) THEN
                RAISE EXCEPTION 'Phase 4 schema bindings are invalid';
            END IF;
            SELECT COALESCE(jsonb_agg(value ORDER BY value->>'dataset_schema_id',
                value->>'dataset_schema_version'), '[]'::jsonb)
            INTO sorted_schema_bindings
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements(NEW.schema_bindings) AS item(value)
            ) AS values;
            IF NEW.schema_bindings IS DISTINCT FROM sorted_schema_bindings THEN
                RAISE EXCEPTION 'Phase 4 schema bindings must be unique and sorted';
            END IF;

            expected_mapping := jsonb_build_object(
                'mapping_id', NEW.mapping_id::text,
                'mapping_version', NEW.mapping_version,
                'mapping_input_sha256', NEW.mapping_input_sha256,
                'mapper_rule_set_version', NEW.mapper_rule_set_version,
                'mapper_rule_set_sha256', NEW.mapper_rule_set_sha256,
                'canonical_family', NEW.canonical_family,
                'verdict', NEW.verdict,
                'official_corroboration_source_version_ids',
                    NEW.official_corroboration_source_version_ids
            );
            expected_rights := jsonb_build_object(
                'entitlement_id', NEW.entitlement_id,
                'use_rights_id', NEW.use_rights_id,
                'scope', NEW.scope,
                'storage_allowed', NEW.storage_allowed,
                'display_allowed', NEW.display_allowed,
                'non_display_allowed', NEW.non_display_allowed,
                'derived_data_allowed', NEW.derived_data_allowed,
                'redistribution_allowed', NEW.redistribution_allowed
            );

            IF NEW.request_fingerprint_canonical_json::jsonb
                    IS DISTINCT FROM NEW.request_fingerprint_payload
                OR encode(
                    sha256(
                        convert_to('phase4-request-fingerprint-v1', 'UTF8')
                        || decode('00', 'hex')
                        || convert_to(NEW.request_fingerprint_canonical_json, 'UTF8')
                    ),
                    'hex'
                ) IS DISTINCT FROM NEW.request_fingerprint_sha256 THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint hash mismatch';
            END IF;
            IF NEW.request_fingerprint_payload->>'fingerprint_version'
                    <> NEW.request_fingerprint_version
                OR NEW.request_fingerprint_payload->>'snapshot_schema_version'
                    <> NEW.snapshot_schema_version
                OR NEW.request_fingerprint_payload->>'canonicalization_version'
                    <> NEW.canonicalization_version
                OR NEW.request_fingerprint_payload->>'date_only_availability_convention'
                    <> NEW.date_only_availability_convention
                OR NEW.request_fingerprint_payload#>'{{request,mapping}}'
                    IS DISTINCT FROM expected_mapping
                OR (NEW.request_fingerprint_payload#>>'{{request,as_of_utc}}')::timestamptz
                    IS DISTINCT FROM NEW.as_of_utc
                OR NEW.request_fingerprint_payload#>>'{{request,capability}}'
                    <> NEW.capability
                OR NEW.request_fingerprint_payload#>>'{{request,mock_configuration_id}}'
                    <> NEW.mock_configuration_id THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint request mismatch';
            END IF;
            IF NEW.request_fingerprint_payload#>>'{{adapter,provider_id}}' <> NEW.provider_id
                OR NEW.request_fingerprint_payload#>>'{{adapter,adapter_id}}' <> NEW.adapter_id
                OR NEW.request_fingerprint_payload#>>'{{adapter,adapter_version}}'
                    <> NEW.adapter_version
                OR NEW.request_fingerprint_payload#>>'{{adapter,dataset_id}}' <> NEW.dataset_id
                OR NEW.request_fingerprint_payload#>>'{{adapter,product_id}}' <> NEW.product_id
                OR (NEW.request_fingerprint_payload#>>'{{adapter,synthetic}}')::boolean
                    IS DISTINCT FROM NEW.synthetic
                OR NEW.request_fingerprint_payload#>'{{adapter,capabilities}}'
                    IS DISTINCT FROM NEW.capabilities
                OR NEW.request_fingerprint_payload#>'{{adapter,schema_bindings}}'
                    IS DISTINCT FROM NEW.schema_bindings
                OR NEW.request_fingerprint_payload#>'{{adapter,use_rights}}'
                    IS DISTINCT FROM expected_rights
                OR NEW.request_fingerprint_payload->'schema_bindings'
                    IS DISTINCT FROM NEW.schema_bindings
                OR NEW.request_fingerprint_payload->'use_rights'
                    IS DISTINCT FROM expected_rights THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint adapter mismatch';
            END IF;
            IF NEW.request_fingerprint_payload#>>'{{configuration,configuration_id}}'
                    <> NEW.configuration_id
                OR NEW.request_fingerprint_payload#>>'{{configuration,configuration_sha256}}'
                    <> NEW.configuration_sha256
                OR NEW.request_fingerprint_payload#>>'{{configuration,fixture_set_version}}'
                    <> NEW.fixture_set_version THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint configuration mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """


def _phase4_record_type_constraint(*, extended: bool) -> str:
    values = (
        "'instrument_identity','listing_identity','universe_membership',"
        "'ohlcv_bar','corporate_action','delisting_event',"
        "'as_reported_fundamental','calendar_session',"
        "'official_document_event','volatility_return_input'"
    )
    if extended:
        values += (
            ",'sector_classification','official_document_content','social_attention'"
            ",'macro_rate_observation','crisis_window_definition'"
        )
    return values


def _phase4_normalized_identity_scope_bridge_sql(*, extended: bool) -> str:
    base_scope = r"""            IF normalized_record_type <> 'calendar_session'
                    AND NEW.instrument_id IS NULL
                OR normalized_record_type IN (
                    'listing_identity','universe_membership','ohlcv_bar',
                    'delisting_event','volatility_return_input'
                ) AND NEW.listing_id IS NULL
                OR normalized_record_type IN ('instrument_identity','calendar_session')
                    AND NEW.listing_id IS NOT NULL
                OR normalized_record_type = 'calendar_session'
                    AND NEW.instrument_id IS NOT NULL THEN"""
    extended_scope = r"""            IF normalized_record_type NOT IN (
                    'calendar_session','macro_rate_observation',
                    'crisis_window_definition'
                ) AND NEW.instrument_id IS NULL
                OR normalized_record_type IN (
                    'listing_identity','universe_membership','ohlcv_bar',
                    'delisting_event','volatility_return_input'
                ) AND NEW.listing_id IS NULL
                OR normalized_record_type IN (
                    'instrument_identity','calendar_session','macro_rate_observation',
                    'crisis_window_definition'
                ) AND NEW.listing_id IS NOT NULL
                OR normalized_record_type IN (
                    'calendar_session','macro_rate_observation','crisis_window_definition'
                ) AND NEW.instrument_id IS NOT NULL THEN"""
    source_scope, target_scope = (
        (base_scope, extended_scope) if extended else (extended_scope, base_scope)
    )
    return f"""
        DO $phase6_normalized_scope$
        DECLARE
            function_sql text;
            replaced_sql text;
        BEGIN
            SELECT pg_get_functiondef(
                'validate_phase4_normalized_observation()'::regprocedure
            ) INTO function_sql;
            replaced_sql := replace(
                function_sql,
                $phase6_scope_source${source_scope}$phase6_scope_source$,
                $phase6_scope_target${target_scope}$phase6_scope_target$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION
                    'Phase 6 could not bridge normalized global identity scope';
            END IF;
            EXECUTE replaced_sql;
        END;
        $phase6_normalized_scope$;
    """


def _phase5_source_lineage_bridge_sql() -> str:
    return r"""
        CREATE FUNCTION phase6_source_payload_equivalent(
            checked_capability text,
            left_value jsonb,
            right_value jsonb
        ) RETURNS boolean AS $$
        DECLARE
            rate_field text;
            numeric_pattern constant text := '^[+-]?[0-9]+([.][0-9]+)?$';
        BEGIN
            IF checked_capability IS DISTINCT FROM 'macro_regime_inputs'
               OR left_value->>'record_type'
                    IS DISTINCT FROM 'macro_rate_observation'
               OR right_value->>'record_type'
                    IS DISTINCT FROM 'macro_rate_observation' THEN
                RETURN phase5_json_payload_equivalent(left_value, right_value);
            END IF;

            IF jsonb_typeof(left_value) IS DISTINCT FROM 'object'
               OR jsonb_typeof(right_value) IS DISTINCT FROM 'object'
               OR NOT left_value ?& ARRAY[
                    'rate_value','previous_rate_value','rate_change'
               ]
               OR NOT right_value ?& ARRAY[
                    'rate_value','previous_rate_value','rate_change'
               ]
               OR NOT phase5_json_payload_equivalent(
                    left_value - ARRAY[
                        'rate_value','previous_rate_value','rate_change'
                    ]::text[],
                    right_value - ARRAY[
                        'rate_value','previous_rate_value','rate_change'
                    ]::text[]
               ) THEN
                RETURN FALSE;
            END IF;

            FOREACH rate_field IN ARRAY ARRAY[
                'rate_value','previous_rate_value','rate_change'
            ]
            LOOP
                IF jsonb_typeof(left_value->rate_field) IS DISTINCT FROM 'string'
                   OR jsonb_typeof(right_value->rate_field) IS DISTINCT FROM 'string'
                   OR left_value->>rate_field !~ numeric_pattern
                   OR right_value->>rate_field !~ numeric_pattern
                   OR (left_value->>rate_field)::numeric
                        IS DISTINCT FROM (right_value->>rate_field)::numeric THEN
                    RETURN FALSE;
                END IF;
            END LOOP;
            RETURN TRUE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;

        CREATE FUNCTION phase6_sha256_prefix64_fraction(checked_value text)
        RETURNS numeric AS $$
        DECLARE
            accumulator numeric := 0;
            character_index integer;
            digit_value integer;
        BEGIN
            IF checked_value !~ '^[0-9a-f]{64}$' THEN
                RETURN NULL;
            END IF;
            FOR character_index IN 1..16 LOOP
                digit_value := strpos(
                    '0123456789abcdef',
                    substr(checked_value, character_index, 1)
                ) - 1;
                accumulator := accumulator * 16 + digit_value;
            END LOOP;
            -- Exact 64-place reciprocal of 18446744073709551616 (2^64).
            -- A direct numeric division would silently round to 20 places.
            RETURN accumulator
                * 0.0000000000000000000542101086242752217003726400434970855712890625;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT;

        DO $phase6_bridge$
        DECLARE
            function_sql text;
            replaced_sql text;
        BEGIN
            SELECT pg_get_functiondef(
                'validate_phase5_report_source_lineage(uuid)'::regprocedure
            ) INTO function_sql;
            IF function_sql IS NULL THEN
                RAISE EXCEPTION 'Phase 6 requires the Phase 5 source-lineage validator';
            END IF;

            EXECUTE 'ALTER FUNCTION validate_phase5_report_source_lineage(uuid) '
                    'RENAME TO validate_phase5_report_source_lineage_phase5_base';

            replaced_sql := replace(
                function_sql,
$o$               OR NOT phase5_json_payload_equivalent(
                    source_item#>'{normalized_observation,payload}',
                    observation.payload
               )$o$,
$n$               OR NOT phase6_source_payload_equivalent(
                    source_item#>>'{key,capability}',
                    source_item#>'{normalized_observation,payload}',
                    observation.payload
               )$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION
                    'Phase 6 could not extend macro source-payload equivalence';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$               OR jsonb_typeof(lineage_item->'membership_source_observation_key')
                    <> 'object'
               OR lineage_item#>>'{membership_source_observation_key,capability}'
                    IS DISTINCT FROM 'universe_membership'$o$,
$n$               OR jsonb_typeof(lineage_item->'membership_source_observation_key')
                    IS NULL
               OR jsonb_typeof(lineage_item->'membership_source_observation_key')
                    NOT IN ('object','null')
               OR (
                    jsonb_typeof(lineage_item->'membership_source_observation_key')
                        = 'object'
                    AND lineage_item#>>'{membership_source_observation_key,capability}'
                        IS DISTINCT FROM 'universe_membership'
               )$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not extend the membership lineage shape';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$               OR lineage_item#>>'{feature_derivation,schema_version}'
                    IS DISTINCT FROM 'phase5-source-feature-derivation-v1'
               OR lineage_item#>>'{feature_derivation,formula_id}'
                    IS DISTINCT FROM 'source-decimal-times-frozen-multiplier-v1'
               OR lineage_item#>>'{feature_derivation,source_payload_field}'
                    NOT IN ('open','volume')$o$,
$n$               OR lineage_item#>>'{feature_derivation,schema_version}'
                    NOT IN (
                        'phase5-source-feature-derivation-v1',
                        'phase5-source-feature-derivation-v2',
                        'phase6-source-feature-derivation-v1'
                    )
               OR (
                    lineage_item#>>'{feature_derivation,schema_version}'
                        = 'phase5-source-feature-derivation-v1'
                    AND (
                        lineage_item#>>'{feature_derivation,formula_id}'
                            IS DISTINCT FROM
                                'source-decimal-times-frozen-multiplier-v1'
                        OR lineage_item#>>'{feature_derivation,source_payload_field}'
                            NOT IN ('open','volume')
                    )
               )
               OR (
                    lineage_item#>>'{feature_derivation,schema_version}'
                        = 'phase5-source-feature-derivation-v2'
                    AND (
                        lineage_item#>>'{feature_derivation,formula_id}'
                            IS DISTINCT FROM
                                'source-sha256-prefix64-times-frozen-multiplier-v1'
                        OR lineage_item#>>'{feature_derivation,source_payload_field}'
                            IS DISTINCT FROM 'document_content_sha256'
                        OR lineage_item#>>'{feature_derivation,source_observation_key,capability}'
                            IS DISTINCT FROM 'official_document_event_metadata'
                    )
               )
               OR (
                    lineage_item#>>'{feature_derivation,schema_version}'
                        = 'phase6-source-feature-derivation-v1'
                    AND (
                        lineage_item#>>'{feature_derivation,formula_id}'
                            IS DISTINCT FROM
                                'source-decimal-times-frozen-multiplier-quantized-1e-12-v1'
                        OR lineage_item#>>'{feature_derivation,source_payload_field}'
                            NOT IN ('open','volume')
                    )
               )$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not extend the derivation vocabulary';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$               OR (
                    resolved.source_item#>'{normalized_observation,payload}'
                        ->> (lineage_item#>>'{feature_derivation,source_payload_field}')
                  )::numeric
                    * (lineage_item#>>'{feature_derivation,multiplier}')::numeric
                    IS DISTINCT FROM
                        (lineage_item#>>'{feature_derivation,derived_feature_value}')::numeric;$o$,
$n$               OR CASE
                    WHEN lineage_item#>>'{feature_derivation,schema_version}'
                            = 'phase5-source-feature-derivation-v1' THEN
                        (
                            resolved.source_item#>'{normalized_observation,payload}'
                                ->> (
                                    lineage_item
                                        #>>'{feature_derivation,source_payload_field}'
                                )
                        )::numeric
                            * (
                                lineage_item#>>'{feature_derivation,multiplier}'
                            )::numeric
                            IS DISTINCT FROM (
                                lineage_item#>>'{feature_derivation,derived_feature_value}'
                            )::numeric
                    WHEN lineage_item#>>'{feature_derivation,schema_version}'
                            = 'phase5-source-feature-derivation-v2' THEN
                        phase6_sha256_prefix64_fraction(
                            resolved.source_item#>'{normalized_observation,payload}'
                                ->> 'document_content_sha256'
                        ) * (
                            lineage_item#>>'{feature_derivation,multiplier}'
                        )::numeric
                            IS DISTINCT FROM (
                                lineage_item#>>'{feature_derivation,derived_feature_value}'
                            )::numeric
                    WHEN lineage_item#>>'{feature_derivation,schema_version}'
                            = 'phase6-source-feature-derivation-v1' THEN
                        round(
                            (
                                resolved.source_item#>'{normalized_observation,payload}'
                                    ->> (
                                        lineage_item
                                            #>>'{feature_derivation,source_payload_field}'
                                    )
                            )::numeric
                                * (
                                    lineage_item#>>'{feature_derivation,multiplier}'
                                )::numeric,
                            12
                        ) IS DISTINCT FROM (
                            lineage_item#>>'{feature_derivation,derived_feature_value}'
                        )::numeric
                    ELSE TRUE
               END;$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not extend the derivation computation';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$            SELECT count(*) INTO invalid_lineage_capability_count
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
            ) IS DISTINCT FROM required_capabilities;$o$,
$n$            SELECT count(*) INTO invalid_lineage_capability_count
            FROM jsonb_array_elements(report_row.sample_lineage)
                AS lineage(lineage_item)
            WHERE EXISTS (
                SELECT 1
                FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                    AS ref(ref_item)
                WHERE NOT (
                    required_capabilities @> jsonb_build_array(
                        to_jsonb(ref_item->>'capability')
                    )
                )
            );

            IF (
                SELECT COALESCE(
                    jsonb_agg(to_jsonb(capability) ORDER BY capability),
                    '[]'::jsonb
                )
                FROM (
                    SELECT DISTINCT source_item#>>'{key,capability}' AS capability
                    FROM jsonb_array_elements(report_row.source_observations)
                        AS source(source_item)
                ) AS report_capabilities
            ) IS DISTINCT FROM required_capabilities THEN
                invalid_lineage_capability_count :=
                    invalid_lineage_capability_count + 1;
            END IF;$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not generalize sample-scoped capability lineage';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$            SELECT count(*) INTO unused_source_count
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
            );$o$,
$n$            SELECT count(*) INTO unused_source_count
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
            )
              AND NOT (
                    required_capabilities @> jsonb_build_array(
                        to_jsonb(source_item#>>'{key,capability}')
                    )
              );$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not permit report-wide capability witnesses';
            END IF;
            function_sql := replaced_sql;

            replaced_sql := replace(
                function_sql,
$o$            IF invalid_lineage_count <> 0$o$,
$n$            SELECT count(*) INTO invalid_membership_count
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
            WHERE (
                jsonb_typeof(lineage_item->'membership_source_observation_key') = 'null'
                AND (
                    EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                            AS ref(ref_item)
                        WHERE ref_item->>'capability' = 'universe_membership'
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(
                            (lineage_item->'feature_dependency_ids')
                            || (lineage_item->'target_dependency_ids')
                        ) AS dependency(dependency_id)
                        WHERE dependency_id LIKE 'phase4-universe_membership.%'
                    )
                    OR jsonb_typeof(lineage_item->'universe_membership')
                        IS DISTINCT FROM 'null'
                    OR lineage_item#>>'{feature_derivation,source_observation_key,capability}'
                        = 'universe_membership'
                )
            ) OR (
                jsonb_typeof(lineage_item->'membership_source_observation_key') = 'object'
                AND (
                    membership_source.source_item IS NULL
                    OR feature_source.source_item IS NULL
                    OR membership_source.source_item->>'disposition'
                        NOT IN ('included_as_of','retained_historical_vintage')
                    OR membership_source.source_item
                        #>>'{normalized_observation,payload,record_type}'
                        IS DISTINCT FROM 'universe_membership'
                    OR membership_source.source_item
                        #>>'{normalized_observation,payload,status}'
                        IS DISTINCT FROM 'included'
                    OR (
                        membership_source.source_item
                            #>>'{normalized_observation,available_at}'
                    )::timestamptz > (lineage_item->>'decision_time_utc')::timestamptz
                    OR (
                        membership_source.source_item
                            #>>'{normalized_observation,valid_from}'
                    )::timestamptz > (lineage_item->>'decision_time_utc')::timestamptz
                    OR (
                        membership_source.source_item
                            #>>'{normalized_observation,valid_to}' IS NOT NULL
                        AND (lineage_item->>'decision_time_utc')::timestamptz >=
                            (
                                membership_source.source_item
                                    #>>'{normalized_observation,valid_to}'
                            )::timestamptz
                    )
                    OR membership_source.source_item
                        #>>'{normalized_observation,instrument_id}'
                        IS DISTINCT FROM feature_source.source_item
                            #>>'{normalized_observation,instrument_id}'
                    OR membership_source.source_item
                        #>>'{normalized_observation,listing_id}'
                        IS DISTINCT FROM feature_source.source_item
                            #>>'{normalized_observation,listing_id}'
                    OR NOT EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements(lineage_item->'source_observation_refs')
                            AS ref(ref_item)
                        WHERE ref_item->>'capability' = 'universe_membership'
                          AND ref_item->>'normalized_observation_id' =
                                lineage_item
                                    #>>'{membership_source_observation_key,normalized_observation_id}'
                    )
                )
            );

            IF invalid_lineage_count <> 0$n$
            );
            IF replaced_sql IS NOT DISTINCT FROM function_sql THEN
                RAISE EXCEPTION 'Phase 6 could not extend the membership role validator';
            END IF;

            EXECUTE replaced_sql;
        END;
        $phase6_bridge$;
    """


def upgrade() -> None:
    # Additive prerequisites for the authorized Phase 6 research families.
    op.drop_constraint(
        "ck_data_snapshot_capability",
        "data_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_capability",
        "data_snapshots",
        _phase4_snapshot_capability_constraint(extended=True),
    )
    op.drop_constraint(
        "ck_data_snapshot_frozen_versions",
        "data_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_frozen_versions",
        "data_snapshots",
        _phase4_snapshot_frozen_versions_constraint(extended=True),
    )
    op.drop_constraint(
        "ck_data_quality_finding_identities",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_identities",
        "data_quality_findings",
        _phase4_quality_finding_identity_constraint(extended=True),
    )
    op.drop_constraint(
        "ck_data_quality_finding_code",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_code",
        "data_quality_findings",
        _phase4_quality_finding_code_constraint(extended=True),
    )
    op.drop_constraint(
        "ck_data_snapshot_constituent_record_type",
        "data_snapshot_constituents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_constituent_record_type",
        "data_snapshot_constituents",
        f"record_type IN ({_phase4_record_type_constraint(extended=True)})",
    )
    op.drop_constraint(
        "ck_data_quality_finding_record_type",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_record_type",
        "data_quality_findings",
        "affected_record_type IS NULL OR affected_record_type IN ("
        f"{_phase4_record_type_constraint(extended=True)})",
    )
    op.execute(_phase4_record_type_function(extended=True))
    op.execute(_phase4_snapshot_request_function(extended=True))
    op.execute(_phase4_normalized_identity_scope_bridge_sql(extended=True))

    # Preserve the byte-identical Phase 5 validator under a private name, then
    # install only the two additive Phase 6 lineage shapes. Downgrade restores
    # the preserved function instead of trying to reconstruct it.
    op.execute(_phase5_source_lineage_bridge_sql())

    op.create_table(
        "research_pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("configuration_id", sa.String(length=256), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_family", sa.String(length=64), nullable=False),
        sa.Column("specification_sha256", sa.String(length=64), nullable=False),
        sa.Column("feature_lineage_sha256", sa.String(length=64), nullable=False),
        sa.Column("snapshot_bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("phase5_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phase5_policy_version", sa.Integer(), nullable=False),
        sa.Column("phase5_policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("phase5_fixture_id", sa.String(length=256), nullable=False),
        sa.Column("phase5_fixture_sha256", sa.String(length=64), nullable=False),
        sa.Column("evaluation_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluation_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promotion_state", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        _payload("artifact_payload"),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("no_real_performance_claimed", sa.Boolean(), nullable=False),
        sa.Column("paper_approval_granted", sa.Boolean(), nullable=False),
        _created_at(),
        _hash_check(
            (
                "request_fingerprint_sha256",
                "artifact_sha256",
                "configuration_sha256",
                "specification_sha256",
                "feature_lineage_sha256",
                "snapshot_bundle_sha256",
                "phase5_policy_sha256",
                "phase5_fixture_sha256",
            ),
            name="ck_research_pipeline_run_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase6-research-artifact-v2' "
            "AND configuration_id IN ("
            "'phase6-a-pass-v2','phase6-a-fail-cost-v2',"
            "'phase6-b-pass-v2','phase6-b-fail-crash-v2',"
            "'phase6-c-pass-v2','phase6-c-fail-corroboration-v2') "
            "AND phase5_policy_version >= 1 "
            "AND btrim(phase5_fixture_id) <> ''",
            name="ck_research_pipeline_run_identity",
        ),
        sa.CheckConstraint(
            "canonical_family IN ("
            "'A_CROSS_SECTIONAL_EQUITY_RANKING',"
            "'B_TIME_SERIES_MOMENTUM_REGIME',"
            "'C_OFFICIAL_EVENT_TEXT_OVERLAY')",
            name="ck_research_pipeline_run_family",
        ),
        sa.CheckConstraint(
            "promotion_state IN ("
            "'PASS_RESEARCH','FAIL_REJECT','BLOCKED_MISSING_POLICY',"
            "'BLOCKED_UNCOMPUTABLE','RESEARCH_ONLY_REGIME_DEPENDENT')",
            name="ck_research_pipeline_run_promotion_state",
        ),
        sa.CheckConstraint(
            "(evaluation_report_id IS NOT NULL) <> (evaluation_outcome_id IS NOT NULL) "
            "AND ((status = 'completed' AND promotion_state IN ("
            "'PASS_RESEARCH','FAIL_REJECT','RESEARCH_ONLY_REGIME_DEPENDENT')) OR "
            "(status = 'blocked' AND promotion_state IN ("
            "'BLOCKED_MISSING_POLICY','BLOCKED_UNCOMPUTABLE'))) "
            "AND (evaluation_outcome_id IS NULL OR status = 'blocked')",
            name="ck_research_pipeline_run_terminal_binding",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(artifact_payload) = 'object' "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_typeof(warnings) = 'array' "
            "AND no_real_performance_claimed "
            "AND NOT paper_approval_granted "
            "AND (artifact_payload->>'synthetic')::boolean "
            "AND (artifact_payload->>'pass_research_is_not_paper_approval')::boolean "
            "AND (artifact_payload->>'no_real_performance_claimed')::boolean "
            "AND NOT (artifact_payload->>'paper_approval_granted')::boolean "
            "AND artifact_payload->>'code_version_git_sha' ~ '^[0-9a-f]{40}$' "
            "AND (artifact_payload->>'random_seed')::bigint >= 0 "
            "AND (artifact_payload#>>'{phase5_evaluation,raw_trial_count}')::bigint >= 0 "
            "AND (artifact_payload#>>'{phase5_evaluation,effective_trial_count}')::numeric >= 0",
            name="ck_research_pipeline_run_research_only",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["research_mapping_versions.id"],
            name="fk_research_pipeline_run_mapping",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["phase5_policy_id", "phase5_policy_version", "phase5_policy_sha256"],
            [
                "evaluation_policies.policy_id",
                "evaluation_policies.policy_version",
                "evaluation_policies.policy_sha256",
            ],
            name="fk_research_pipeline_run_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_report_id"],
            ["evaluation_reports.report_id"],
            name="fk_research_pipeline_run_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_outcome_id"],
            ["evaluation_blocked_outcomes.outcome_id"],
            name="fk_research_pipeline_run_outcome",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_pipeline_runs"),
        sa.UniqueConstraint(
            "request_fingerprint_sha256",
            name="uq_research_pipeline_run_request_fingerprint",
        ),
        sa.UniqueConstraint(
            "artifact_sha256",
            name="uq_research_pipeline_run_artifact_sha256",
        ),
    )
    op.create_index(
        "ix_research_pipeline_runs_family_created",
        "research_pipeline_runs",
        ["canonical_family", "created_at_utc", "id"],
    )

    op.create_table(
        "research_pipeline_snapshot_bindings",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("binding_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("snapshot_sha256", "binding_sha256"),
            name="ck_research_pipeline_snapshot_binding_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 AND capability IN ("
            "'security_master','universe_membership','ohlcv','corporate_actions',"
            "'delistings','as_reported_fundamentals','trading_calendar',"
            "'volatility_return_inputs','official_document_event_metadata',"
            "'macro_regime_inputs') "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_research_pipeline_snapshot_binding_identity",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_pipeline_snapshot_binding_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_research_pipeline_snapshot_binding_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_sha256"],
            ["data_snapshots.snapshot_sha256"],
            name="fk_research_pipeline_snapshot_binding_snapshot_sha",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "ordinal",
            name="pk_research_pipeline_snapshot_bindings",
        ),
        sa.UniqueConstraint(
            "run_id",
            "binding_sha256",
            name="uq_research_pipeline_snapshot_binding_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "snapshot_id",
            name="uq_research_pipeline_snapshot_binding_snapshot",
        ),
        sa.UniqueConstraint(
            "run_id",
            "capability",
            name="uq_research_pipeline_snapshot_binding_capability",
        ),
    )

    op.create_table(
        "research_pipeline_attempts",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("phase5_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phase5_trial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phase5_trial_key", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("config_sha256", sa.String(length=64), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        _payload(),
        sa.Column("attempt_sha256", sa.String(length=64), nullable=False),
        _created_at(),
        _hash_check(
            ("config_sha256", "attempt_sha256"),
            name="ck_research_pipeline_attempt_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 "
            "AND status IN ('completed','failed','abandoned','no_return','blocked') "
            "AND ((phase5_report_id IS NULL AND phase5_trial_id IS NULL "
            "AND phase5_trial_key IS NULL) OR "
            "(phase5_report_id IS NOT NULL AND phase5_trial_id IS NOT NULL "
            "AND phase5_trial_key IS NOT NULL AND btrim(phase5_trial_key) <> '')) "
            "AND ((status = 'completed' AND failure_reason IS NULL) OR "
            "(status IN ('failed','abandoned','no_return','blocked') "
            "AND failure_reason IS NOT NULL AND btrim(failure_reason) <> '')) "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_research_pipeline_attempt_status",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_pipeline_attempt_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["phase5_report_id", "phase5_trial_id"],
            ["evaluation_trials.report_id", "evaluation_trials.trial_id"],
            name="fk_research_pipeline_attempt_trial",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "ordinal",
            name="pk_research_pipeline_attempts",
        ),
        sa.UniqueConstraint(
            "run_id",
            "attempt_sha256",
            name="uq_research_pipeline_attempt_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "phase5_trial_id",
            name="uq_research_pipeline_attempt_trial",
        ),
        sa.UniqueConstraint(
            "run_id",
            "phase5_trial_key",
            name="uq_research_pipeline_attempt_trial_key",
        ),
    )

    op.create_table(
        "research_feature_rows",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_id", sa.String(length=256), nullable=False),
        sa.Column("entity_id", sa.String(length=256), nullable=False),
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(("row_sha256",), name="ck_research_feature_row_hashes"),
        sa.CheckConstraint(
            "ordinal >= 1 AND btrim(sample_id) <> '' AND btrim(entity_id) <> '' "
            "AND jsonb_typeof(payload) = 'object' "
            "AND NOT (payload ?| ARRAY["
            "'trade_instruction','position_size','allocation','buy_sell_call',"
            "'promotion_verdict','paper_approval'])",
            name="ck_research_feature_row_research_only",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_feature_row_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id", "row_id", name="pk_research_feature_rows"),
        sa.UniqueConstraint(
            "run_id",
            "row_sha256",
            name="uq_research_feature_row_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_research_feature_row_ordinal",
        ),
        sa.UniqueConstraint(
            "run_id",
            "sample_id",
            "entity_id",
            "decision_time_utc",
            name="uq_research_feature_row_semantic_identity",
        ),
    )

    op.create_table(
        "research_score_outputs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("score_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_id", sa.String(length=256), nullable=False),
        sa.Column("model_id", sa.String(length=256), nullable=False),
        sa.Column(
            "research_score",
            sa.Numeric(precision=38, scale=30),
            nullable=False,
        ),
        sa.Column("explanation_sha256", sa.String(length=64), nullable=False),
        sa.Column("output_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("explanation_sha256", "output_sha256"),
            name="ck_research_score_output_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 AND btrim(sample_id) <> '' AND btrim(model_id) <> '' "
            "AND jsonb_typeof(payload) = 'object' "
            "AND NOT (payload ?| ARRAY["
            "'trade_instruction','position_size','allocation','buy_sell_call',"
            "'promotion_verdict','paper_approval'])",
            name="ck_research_score_output_research_only",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_score_output_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id", "score_id", name="pk_research_score_outputs"),
        sa.UniqueConstraint(
            "run_id",
            "output_sha256",
            name="uq_research_score_output_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_research_score_output_ordinal",
        ),
        sa.UniqueConstraint(
            "run_id",
            "sample_id",
            "model_id",
            name="uq_research_score_output_semantic_identity",
        ),
    )

    op.create_table(
        "research_baseline_comparisons",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_model_id", sa.String(length=256), nullable=False),
        sa.Column("baseline_model_id", sa.String(length=256), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("comparison_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("comparison_sha256",),
            name="ck_research_baseline_comparison_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 "
            "AND btrim(candidate_model_id) <> '' "
            "AND btrim(baseline_model_id) <> '' "
            "AND candidate_model_id <> baseline_model_id "
            "AND outcome IN ('survives','rejected') "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_research_baseline_comparison_identity",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_baseline_comparison_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "comparison_id",
            name="pk_research_baseline_comparisons",
        ),
        sa.UniqueConstraint(
            "run_id",
            "comparison_sha256",
            name="uq_research_baseline_comparison_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_research_baseline_comparison_ordinal",
        ),
        sa.UniqueConstraint(
            "run_id",
            "candidate_model_id",
            "baseline_model_id",
            name="uq_research_baseline_comparison_semantic_identity",
        ),
    )

    op.create_table(
        "research_text_extractions",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_sha256", sa.String(length=64), nullable=False),
        sa.Column("extractor_id", sa.String(length=256), nullable=False),
        sa.Column("extractor_version", sa.String(length=128), nullable=False),
        sa.Column("model_id", sa.String(length=256), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("extraction_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("document_sha256", "extraction_sha256"),
            name="ck_research_text_extraction_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 "
            "AND btrim(extractor_id) <> '' AND btrim(extractor_version) <> '' "
            "AND btrim(model_id) <> '' AND btrim(prompt_version) <> '' "
            "AND schema_version = 'phase6-text-feature-extraction-v1' "
            "AND jsonb_typeof(payload) = 'object' "
            "AND NOT (payload ?| ARRAY["
            "'label','signal','model_decision','trade_instruction','position_size',"
            "'allocation','buy_sell_call','promotion_outcome','execution_instruction'])",
            name="ck_research_text_extraction_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_text_extraction_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["research_source_versions.id"],
            name="fk_research_text_extraction_source_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "extraction_id",
            name="pk_research_text_extractions",
        ),
        sa.UniqueConstraint(
            "run_id",
            "extraction_sha256",
            name="uq_research_text_extraction_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_research_text_extraction_ordinal",
        ),
        sa.UniqueConstraint(
            "run_id",
            "source_version_id",
            "document_sha256",
            "extractor_id",
            "extractor_version",
            "model_id",
            "prompt_version",
            "schema_version",
            name="uq_research_text_extraction_semantic_identity",
        ),
    )

    op.create_table(
        "research_text_corroborations",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("corroboration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("social_record_id", sa.String(length=256), nullable=False),
        sa.Column(
            "official_source_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("official_document_sha256", sa.String(length=64), nullable=False),
        sa.Column("corroboration_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("official_document_sha256", "corroboration_sha256"),
            name="ck_research_text_corroboration_hashes",
        ),
        sa.CheckConstraint(
            "ordinal >= 1 AND btrim(social_record_id) <> '' AND jsonb_typeof(payload) = 'object'",
            name="ck_research_text_corroboration_identity",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_pipeline_runs.id"],
            name="fk_research_text_corroboration_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["official_source_version_id"],
            ["research_source_versions.id"],
            name="fk_research_text_corroboration_official_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "corroboration_id",
            name="pk_research_text_corroborations",
        ),
        sa.UniqueConstraint(
            "run_id",
            "corroboration_sha256",
            name="uq_research_text_corroboration_sha256",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_research_text_corroboration_ordinal",
        ),
        sa.UniqueConstraint(
            "run_id",
            "social_record_id",
            "official_source_version_id",
            "official_document_sha256",
            name="uq_research_text_corroboration_semantic_identity",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION own_phase6_created_at_utc()
        RETURNS trigger AS $$
        BEGIN
            NEW.created_at_utc := CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE6_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase6_created_at_utc()
            """
        )

    # Keep the database authority boundary on the same canonical bytes used by
    # the Phase 6 Pydantic contracts. jsonb's built-in text form contains
    # insignificant whitespace, so render recursively before hashing.
    op.execute(
        """
        CREATE FUNCTION phase6_canonical_json(checked_value jsonb)
        RETURNS text AS $$
        DECLARE
            rendered text;
        BEGIN
            CASE jsonb_typeof(checked_value)
                WHEN 'object' THEN
                    SELECT '{' || COALESCE(
                        string_agg(
                            to_jsonb(key)::text || ':' || phase6_canonical_json(value),
                            ',' ORDER BY key COLLATE "C"
                        ),
                        ''
                    ) || '}'
                    INTO rendered
                    FROM jsonb_each(checked_value);
                    RETURN rendered;
                WHEN 'array' THEN
                    SELECT '[' || COALESCE(
                        string_agg(
                            phase6_canonical_json(value),
                            ',' ORDER BY ordinal
                        ),
                        ''
                    ) || ']'
                    INTO rendered
                    FROM jsonb_array_elements(checked_value)
                         WITH ORDINALITY AS item(value, ordinal);
                    RETURN rendered;
                WHEN 'string' THEN
                    RETURN to_jsonb(checked_value #>> ARRAY[]::text[])::text;
                ELSE
                    RETURN checked_value::text;
            END CASE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase6_domain_sha256(hash_domain text, checked_value jsonb)
        RETURNS text AS $$
            SELECT encode(
                sha256(
                    convert_to(hash_domain, 'UTF8')
                    || decode('00', 'hex')
                    || convert_to(phase6_canonical_json(checked_value), 'UTF8')
                ),
                'hex'
            )
        $$ LANGUAGE sql IMMUTABLE STRICT
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase6_sha1(checked_value bytea)
        RETURNS bytea AS $$
        DECLARE
            message bytea;
            original_bit_length bigint;
            block_offset integer;
            word_index integer;
            round_index integer;
            words bigint[];
            h0 bigint := 1732584193;
            h1 bigint := 4023233417;
            h2 bigint := 2562383102;
            h3 bigint := 271733878;
            h4 bigint := 3285377520;
            a bigint;
            b bigint;
            c bigint;
            d bigint;
            e bigint;
            f bigint;
            k bigint;
            temporary bigint;
            mask constant bigint := 4294967295;
        BEGIN
            original_bit_length := octet_length(checked_value)::bigint * 8;
            message := checked_value || decode('80', 'hex');
            WHILE octet_length(message) % 64 <> 56 LOOP
                message := message || decode('00', 'hex');
            END LOOP;
            message := message || decode(
                lpad(to_hex(original_bit_length), 16, '0'),
                'hex'
            );

            block_offset := 0;
            WHILE block_offset < octet_length(message) LOOP
                words := ARRAY[]::bigint[];
                FOR word_index IN 0..15 LOOP
                    words[word_index] := (
                        (get_byte(message, block_offset + word_index * 4)::bigint << 24)
                        | (get_byte(message, block_offset + word_index * 4 + 1)::bigint << 16)
                        | (get_byte(message, block_offset + word_index * 4 + 2)::bigint << 8)
                        | get_byte(message, block_offset + word_index * 4 + 3)::bigint
                    ) & mask;
                END LOOP;
                FOR word_index IN 16..79 LOOP
                    temporary := words[word_index - 3]
                        # words[word_index - 8]
                        # words[word_index - 14]
                        # words[word_index - 16];
                    words[word_index] := (
                        (temporary << 1) | (temporary >> 31)
                    ) & mask;
                END LOOP;

                a := h0;
                b := h1;
                c := h2;
                d := h3;
                e := h4;
                FOR round_index IN 0..79 LOOP
                    IF round_index <= 19 THEN
                        f := ((b & c) | ((~b) & d)) & mask;
                        k := 1518500249;
                    ELSIF round_index <= 39 THEN
                        f := (b # c # d) & mask;
                        k := 1859775393;
                    ELSIF round_index <= 59 THEN
                        f := ((b & c) | (b & d) | (c & d)) & mask;
                        k := 2400959708;
                    ELSE
                        f := (b # c # d) & mask;
                        k := 3395469782;
                    END IF;
                    temporary := (
                        ((a << 5) | (a >> 27)) + f + e + k + words[round_index]
                    ) & mask;
                    e := d;
                    d := c;
                    c := ((b << 30) | (b >> 2)) & mask;
                    b := a;
                    a := temporary;
                END LOOP;
                h0 := (h0 + a) & mask;
                h1 := (h1 + b) & mask;
                h2 := (h2 + c) & mask;
                h3 := (h3 + d) & mask;
                h4 := (h4 + e) & mask;
                block_offset := block_offset + 64;
            END LOOP;

            RETURN decode(
                lpad(to_hex(h0), 8, '0')
                || lpad(to_hex(h1), 8, '0')
                || lpad(to_hex(h2), 8, '0')
                || lpad(to_hex(h3), 8, '0')
                || lpad(to_hex(h4), 8, '0'),
                'hex'
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase6_uuid5(namespace_value uuid, identity_name text)
        RETURNS uuid AS $$
        DECLARE
            hashed bytea;
            rendered text;
        BEGIN
            hashed := phase6_sha1(
                decode(replace(namespace_value::text, '-', ''), 'hex')
                || convert_to(identity_name, 'UTF8')
            );
            hashed := set_byte(hashed, 6, (get_byte(hashed, 6) & 15) | 80);
            hashed := set_byte(hashed, 8, (get_byte(hashed, 8) & 63) | 128);
            rendered := encode(substring(hashed FROM 1 FOR 16), 'hex');
            RETURN (
                substring(rendered FROM 1 FOR 8) || '-'
                || substring(rendered FROM 9 FOR 4) || '-'
                || substring(rendered FROM 13 FOR 4) || '-'
                || substring(rendered FROM 17 FOR 4) || '-'
                || substring(rendered FROM 21 FOR 12)
            )::uuid;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_payload_columns()
        RETURNS trigger AS $$
        DECLARE
            artifact_preimage jsonb;
            request_preimage jsonb;
            expected_hash text;
            evidence_item jsonb;
            nested_item jsonb;
            canonical_values jsonb;
        BEGIN
            IF TG_TABLE_NAME = 'research_pipeline_runs' THEN
                IF (
                    SELECT count(*)
                    FROM jsonb_object_keys(NEW.artifact_payload)
                   ) <> 36
                   OR NOT NEW.artifact_payload ?& ARRAY[
                        'artifact_schema_version',
                        'request_fingerprint_sha256','pipeline_input_sha256',
                        'configuration_id','configuration_sha256','mapping_id',
                        'mapping_version','mapping_input_sha256','family','specification',
                        'snapshot_bindings','calendar_source_references','regime_evidence',
                        'confirmation_interval','boundary_exclusions',
                        'source_reproduction_audit','snapshot_bundle_sha256','feature_rows',
                        'feature_lineage_sha256','scores','model_output_sets',
                        'trial_economics','attempts','baseline_comparisons','family_evidence',
                        'phase5_evaluation','code_version_git_sha','random_seed',
                        'status','reason_codes','warnings','synthetic',
                        'no_real_performance_claimed',
                        'pass_research_is_not_paper_approval','paper_approval_granted',
                        'disclaimer'
                   ]
                   OR jsonb_typeof(NEW.artifact_payload->'specification') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'regime_evidence') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'confirmation_interval') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'source_reproduction_audit') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'family_evidence') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'phase5_evaluation') <> 'object'
                   OR jsonb_typeof(NEW.artifact_payload->'snapshot_bindings') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'snapshot_bindings') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'calendar_source_references') <> 'array'
                   OR jsonb_typeof(NEW.artifact_payload->'boundary_exclusions') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'boundary_exclusions') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'feature_rows') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'feature_rows') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'scores') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'scores') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'model_output_sets') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'model_output_sets') <> 4
                   OR jsonb_typeof(NEW.artifact_payload->'trial_economics') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'trial_economics') <> 4
                   OR jsonb_typeof(NEW.artifact_payload->'attempts') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'attempts') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'baseline_comparisons') <> 'array'
                   OR jsonb_array_length(NEW.artifact_payload->'baseline_comparisons') < 1
                   OR jsonb_typeof(NEW.artifact_payload->'reason_codes') <> 'array'
                   OR jsonb_typeof(NEW.artifact_payload->'warnings') <> 'array'
                   OR jsonb_typeof(NEW.artifact_payload->'mapping_version') <> 'number'
                   OR jsonb_typeof(NEW.artifact_payload->'random_seed') <> 'number'
                   OR jsonb_typeof(NEW.artifact_payload->'synthetic') <> 'boolean'
                   OR jsonb_typeof(
                        NEW.artifact_payload->'no_real_performance_claimed'
                   ) <> 'boolean'
                   OR jsonb_typeof(
                        NEW.artifact_payload->'pass_research_is_not_paper_approval'
                   ) <> 'boolean'
                   OR jsonb_typeof(NEW.artifact_payload->'paper_approval_granted') <> 'boolean'
                   OR NEW.artifact_payload#>>'{specification,schema_version}'
                        <> 'phase6-research-specification-v2'
                   OR NEW.artifact_payload#>>'{regime_evidence,schema_version}'
                        <> 'phase6-prepared-regime-evidence-v2'
                   OR NOT (NEW.artifact_payload->'regime_evidence') ?& ARRAY[
                        'schema_version','evidence_state','rate_definition_id',
                        'rate_observations','crisis_definition_id','crisis_windows',
                        'unavailable_reason','evidence_sha256'
                   ]
                   OR NOT (NEW.artifact_payload->'confirmation_interval') ?& ARRAY[
                        'schema_version','confirmation_id','confirmation_sha256','sample_id',
                        'interval_start_utc','interval_end_utc','opening_rule',
                        'source_references','label_value','label_source_references',
                        'label_opened'
                   ]
                   OR NOT (NEW.artifact_payload->'source_reproduction_audit') ?& ARRAY[
                        'schema_version','audit_id','audit_sha256','configuration_id',
                        'snapshot_bindings','snapshot_set_sha256',
                        'supplied_pipeline_input_sha256',
                        'reproduced_pipeline_input_sha256','supplied_payload_sha256',
                        'reproduced_payload_sha256','exact_match'
                   ]
                   OR NOT (NEW.artifact_payload->'phase5_evaluation') ?& ARRAY[
                        'policy_id','policy_version','policy_sha256','fixture_id',
                        'fixture_sha256','config_hash','snapshot_bundle_sha256',
                        'evaluation_report_id','evaluation_report_sha256',
                        'evaluation_outcome_id','promotion_state','gate_codes',
                        'raw_trial_count','effective_trial_count',
                        'phase5_trial_set_sha256'
                   ] THEN
                    RAISE EXCEPTION
                        'Phase 6 run artifact is missing complete typed audit evidence';
                END IF;

                IF EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'calendar_source_references'
                    ) AS item(value)
                    WHERE jsonb_typeof(value) <> 'object'
                       OR NOT value ?& ARRAY[
                            'capability','snapshot_id','snapshot_sha256',
                            'raw_observation_id','observation_revision_id',
                            'normalized_observation_id','raw_payload_sha256',
                            'normalized_content_sha256','record_type','source_record_id',
                            'instrument_id','listing_id','available_at_utc','valid_from_utc',
                            'valid_to_utc'
                       ]
                ) OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'boundary_exclusions'
                    ) AS item(value)
                    WHERE jsonb_typeof(value) <> 'object'
                       OR NOT value ?& ARRAY[
                            'schema_version','exclusion_id','exclusion_sha256','sample_id',
                            'decision_time_utc','label_t0_utc','label_t1_utc',
                            'exclusion_rule','label_value','label_source_references',
                            'label_opened'
                       ]
                ) OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'model_output_sets'
                    ) AS item(value)
                    WHERE jsonb_typeof(value) <> 'object'
                       OR NOT value ?& ARRAY[
                            'schema_version','ordinal','output_set_id','output_set_sha256',
                            'model_output_sha256','trial_key','model_id','output_semantics',
                            'outputs','ledger_cells'
                       ]
                       OR value->>'schema_version'
                            <> 'phase6-phase5-model-output-set-v2'
                       OR jsonb_typeof(value->'outputs') <> 'array'
                       OR jsonb_array_length(value->'outputs') < 1
                       OR jsonb_typeof(value->'ledger_cells') <> 'array'
                       OR jsonb_array_length(value->'ledger_cells') < 1
                ) OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'trial_economics'
                    ) AS item(value)
                    WHERE jsonb_typeof(value) <> 'object'
                       OR NOT value ?& ARRAY[
                            'schema_version','ordinal','trial_key','model_id',
                            'output_set_sha256','sample_economics','cost_set_sha256',
                            'economics_sha256'
                       ]
                       OR value->>'schema_version' <> 'phase6-trial-economics-v1'
                       OR jsonb_typeof(value->'sample_economics') <> 'array'
                       OR jsonb_array_length(value->'sample_economics') < 1
                ) THEN
                    RAISE EXCEPTION
                        'Phase 6 run artifact contains incomplete nested audit evidence';
                END IF;

                IF NEW.artifact_payload->>'artifact_schema_version'
                        IS DISTINCT FROM NEW.schema_version
                   OR NEW.artifact_payload->>'request_fingerprint_sha256'
                        IS DISTINCT FROM NEW.request_fingerprint_sha256
                   OR NEW.artifact_payload->>'configuration_id'
                        IS DISTINCT FROM NEW.configuration_id
                   OR NEW.artifact_payload->>'configuration_sha256'
                        IS DISTINCT FROM NEW.configuration_sha256
                   OR (NEW.artifact_payload->>'mapping_id')::uuid
                        IS DISTINCT FROM NEW.mapping_id
                   OR NEW.artifact_payload->>'family' IS DISTINCT FROM NEW.canonical_family
                   OR NEW.artifact_payload#>>'{specification,specification_sha256}'
                        IS DISTINCT FROM NEW.specification_sha256
                   OR NEW.artifact_payload->>'feature_lineage_sha256'
                        IS DISTINCT FROM NEW.feature_lineage_sha256
                   OR NEW.artifact_payload->>'snapshot_bundle_sha256'
                        IS DISTINCT FROM NEW.snapshot_bundle_sha256
                   OR (NEW.artifact_payload#>>'{phase5_evaluation,policy_id}')::uuid
                        IS DISTINCT FROM NEW.phase5_policy_id
                   OR (NEW.artifact_payload#>>'{phase5_evaluation,policy_version}')::integer
                        IS DISTINCT FROM NEW.phase5_policy_version
                   OR NEW.artifact_payload#>>'{phase5_evaluation,policy_sha256}'
                        IS DISTINCT FROM NEW.phase5_policy_sha256
                   OR NEW.artifact_payload#>>'{phase5_evaluation,fixture_id}'
                        IS DISTINCT FROM NEW.phase5_fixture_id
                   OR NEW.artifact_payload#>>'{phase5_evaluation,fixture_sha256}'
                        IS DISTINCT FROM NEW.phase5_fixture_sha256
                   OR (NEW.artifact_payload#>>'{phase5_evaluation,evaluation_report_id}')::uuid
                        IS DISTINCT FROM NEW.evaluation_report_id
                   OR (NEW.artifact_payload#>>'{phase5_evaluation,evaluation_outcome_id}')::uuid
                        IS DISTINCT FROM NEW.evaluation_outcome_id
                   OR NEW.artifact_payload#>>'{phase5_evaluation,promotion_state}'
                        IS DISTINCT FROM NEW.promotion_state
                   OR NEW.artifact_payload->>'status' IS DISTINCT FROM NEW.status
                   OR NEW.artifact_payload->'reason_codes' IS DISTINCT FROM NEW.reason_codes
                   OR NEW.artifact_payload->'warnings' IS DISTINCT FROM NEW.warnings
                   OR (NEW.artifact_payload->>'no_real_performance_claimed')::boolean
                        IS DISTINCT FROM NEW.no_real_performance_claimed
                   OR (NEW.artifact_payload->>'paper_approval_granted')::boolean
                        IS DISTINCT FROM NEW.paper_approval_granted THEN
                    RAISE EXCEPTION 'Phase 6 run payload differs from bound columns';
                END IF;

                artifact_preimage := NEW.artifact_payload;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-artifact-v2',
                    artifact_preimage
                );
                IF expected_hash IS DISTINCT FROM NEW.artifact_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 research artifact canonical hash mismatch';
                END IF;

                request_preimage := jsonb_build_object(
                    'mapping_id', NEW.artifact_payload->'mapping_id',
                    'mapping_version', NEW.artifact_payload->'mapping_version',
                    'mapping_input_sha256', NEW.artifact_payload->'mapping_input_sha256',
                    'snapshot_bundle_sha256', NEW.artifact_payload->'snapshot_bundle_sha256',
                    'configuration_id', NEW.artifact_payload->'configuration_id',
                    'configuration_sha256', NEW.artifact_payload->'configuration_sha256',
                    'specification_sha256',
                        NEW.artifact_payload#>'{specification,specification_sha256}',
                    'code_version_git_sha', NEW.artifact_payload->'code_version_git_sha',
                    'random_seed', NEW.artifact_payload->'random_seed',
                    'pipeline_input_sha256', NEW.artifact_payload->'pipeline_input_sha256'
                );
                expected_hash := phase6_domain_sha256(
                    'phase6-research-request-v2',
                    request_preimage
                );
                IF expected_hash IS DISTINCT FROM NEW.request_fingerprint_sha256
                   OR phase6_uuid5(
                        '09972cb7-9a87-543c-a70a-3835ee8e593c'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.id THEN
                    RAISE EXCEPTION 'Phase 6 research request canonical identity mismatch';
                END IF;

                expected_hash := phase6_domain_sha256(
                    'phase6-research-specification-v2',
                    (NEW.artifact_payload->'specification') - 'specification_sha256'::text
                );
                IF expected_hash IS DISTINCT FROM NEW.specification_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 research specification canonical hash mismatch';
                END IF;

                expected_hash := phase6_domain_sha256(
                    'phase6-prepared-regime-evidence-v2',
                    (NEW.artifact_payload->'regime_evidence') - 'evidence_sha256'::text
                );
                IF expected_hash IS DISTINCT FROM
                        NEW.artifact_payload#>>'{regime_evidence,evidence_sha256}' THEN
                    RAISE EXCEPTION 'Phase 6 regime evidence canonical hash mismatch';
                END IF;

                expected_hash := phase6_domain_sha256(
                    'phase6-label-blind-confirmation-interval-v1',
                    (NEW.artifact_payload->'confirmation_interval')
                        - ARRAY['confirmation_id','confirmation_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM
                        NEW.artifact_payload#>>'{confirmation_interval,confirmation_sha256}'
                   OR phase6_uuid5(
                        'e1f51308-3ab0-56d3-9ad8-26258a3b97bd'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM (
                        NEW.artifact_payload#>>'{confirmation_interval,confirmation_id}'
                   )::uuid THEN
                    RAISE EXCEPTION 'Phase 6 confirmation canonical identity mismatch';
                END IF;

                FOR evidence_item IN
                    SELECT value
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'boundary_exclusions'
                    ) AS item(value)
                LOOP
                    expected_hash := phase6_domain_sha256(
                        'phase6-confirmation-boundary-exclusion-v1',
                        evidence_item - ARRAY['exclusion_id','exclusion_sha256']::text[]
                    );
                    IF expected_hash IS DISTINCT FROM evidence_item->>'exclusion_sha256'
                       OR phase6_uuid5(
                            '622404af-e922-599f-98dd-2d7ccb32176c'::uuid,
                            expected_hash
                       ) IS DISTINCT FROM (evidence_item->>'exclusion_id')::uuid THEN
                        RAISE EXCEPTION
                            'Phase 6 boundary exclusion canonical identity mismatch';
                    END IF;
                END LOOP;

                canonical_values :=
                    NEW.artifact_payload#>'{source_reproduction_audit,snapshot_bindings}';
                IF jsonb_typeof(canonical_values) <> 'array'
                   OR jsonb_array_length(canonical_values) < 1
                   OR NOT (
                        canonical_values @> (NEW.artifact_payload->'snapshot_bindings')
                   )
                   OR NOT (
                        (NEW.artifact_payload->'snapshot_bindings') @> canonical_values
                   )
                   OR jsonb_array_length(canonical_values) <>
                        jsonb_array_length(NEW.artifact_payload->'snapshot_bindings')
                   OR phase6_domain_sha256(
                        'phase6-prepared-source-reproduction-snapshot-set-v1',
                        canonical_values
                   ) IS DISTINCT FROM NEW.artifact_payload#>>
                        '{source_reproduction_audit,snapshot_set_sha256}'
                   OR NEW.artifact_payload#>>
                        '{source_reproduction_audit,configuration_id}'
                        IS DISTINCT FROM NEW.configuration_id
                   OR NEW.artifact_payload#>>
                        '{source_reproduction_audit,supplied_pipeline_input_sha256}'
                        IS DISTINCT FROM NEW.artifact_payload->>'pipeline_input_sha256'
                   OR NEW.artifact_payload#>>
                        '{source_reproduction_audit,reproduced_pipeline_input_sha256}'
                        IS DISTINCT FROM NEW.artifact_payload->>'pipeline_input_sha256'
                   OR (NEW.artifact_payload#>>
                        '{source_reproduction_audit,exact_match}')::boolean
                        IS DISTINCT FROM TRUE THEN
                    RAISE EXCEPTION 'Phase 6 source reproduction evidence mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-prepared-source-reproduction-audit-v1',
                    (NEW.artifact_payload->'source_reproduction_audit')
                        - ARRAY['audit_id','audit_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM
                        NEW.artifact_payload#>>'{source_reproduction_audit,audit_sha256}'
                   OR phase6_uuid5(
                        '2c2b48ec-b10c-5de8-8e77-f32455baa214'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM (
                        NEW.artifact_payload#>>'{source_reproduction_audit,audit_id}'
                   )::uuid THEN
                    RAISE EXCEPTION
                        'Phase 6 source reproduction canonical identity mismatch';
                END IF;

                FOR evidence_item IN
                    SELECT value
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'model_output_sets'
                    ) AS item(value)
                LOOP
                    SELECT COALESCE(
                        jsonb_agg(
                            jsonb_build_array(
                                output_item->'sample_id',
                                output_item->'output_value'
                            ) ORDER BY output_item->>'sample_id'
                        ),
                        '[]'::jsonb
                    ) INTO canonical_values
                    FROM jsonb_array_elements(evidence_item->'outputs') AS output(value)
                    CROSS JOIN LATERAL (SELECT output.value AS output_item) AS normalized;
                    IF phase6_domain_sha256(
                            'phase6-model-output-set-v2',
                            canonical_values
                       ) IS DISTINCT FROM evidence_item->>'model_output_sha256' THEN
                        RAISE EXCEPTION 'Phase 6 model output values canonical hash mismatch';
                    END IF;

                    FOR nested_item IN
                        SELECT value
                        FROM jsonb_array_elements(evidence_item->'ledger_cells') AS item(value)
                    LOOP
                        IF nested_item->>'schema_version'
                                <> 'phase6-research-ledger-cell-v2' THEN
                            RAISE EXCEPTION 'Phase 6 research ledger schema mismatch';
                        END IF;
                        canonical_values := jsonb_build_array(
                            nested_item->'sample_id',
                            nested_item->'label_value',
                            nested_item->'label_t0_utc',
                            nested_item->'label_t1_utc',
                            nested_item->'label_source_references'
                        );
                        IF phase6_domain_sha256(
                                'phase6-research-ledger-label-v1',
                                canonical_values
                           ) IS DISTINCT FROM nested_item->>'label_sha256' THEN
                            RAISE EXCEPTION 'Phase 6 research ledger label hash mismatch';
                        END IF;
                        expected_hash := phase6_domain_sha256(
                            'phase6-research-ledger-cell-v2',
                            nested_item - ARRAY['cell_id','cell_sha256']::text[]
                        );
                        IF expected_hash IS DISTINCT FROM nested_item->>'cell_sha256'
                           OR phase6_uuid5(
                                '7f6f32a5-7a42-5b3b-b61b-8deded858289'::uuid,
                                expected_hash
                           ) IS DISTINCT FROM (nested_item->>'cell_id')::uuid THEN
                            RAISE EXCEPTION
                                'Phase 6 research ledger cell canonical identity mismatch';
                        END IF;
                    END LOOP;

                    expected_hash := phase6_domain_sha256(
                        'phase6-phase5-model-output-registry-entry-v2',
                        evidence_item - ARRAY['output_set_id','output_set_sha256']::text[]
                    );
                    IF expected_hash IS DISTINCT FROM evidence_item->>'output_set_sha256'
                       OR phase6_uuid5(
                            '5d4d79be-eaa1-5d41-912c-407d5837bcc1'::uuid,
                            expected_hash
                       ) IS DISTINCT FROM (evidence_item->>'output_set_id')::uuid THEN
                        RAISE EXCEPTION
                            'Phase 6 model output set canonical identity mismatch';
                    END IF;
                END LOOP;

                FOR evidence_item IN
                    SELECT value
                    FROM jsonb_array_elements(
                        NEW.artifact_payload->'trial_economics'
                    ) AS item(value)
                LOOP
                    FOR nested_item IN
                        SELECT value
                        FROM jsonb_array_elements(
                            evidence_item->'sample_economics'
                        ) AS item(value)
                    LOOP
                        IF jsonb_typeof(nested_item) <> 'object'
                           OR NOT nested_item ?& ARRAY[
                                'schema_version','ordinal','sample_id','model_output',
                                'synthetic_research_weight','return_status',
                                'synthetic_gross_return','cost_entries','evidence_sha256'
                           ]
                           OR nested_item->>'schema_version'
                                <> 'phase6-trial-sample-economics-v1'
                           OR jsonb_typeof(nested_item->'cost_entries') <> 'array'
                           OR jsonb_array_length(nested_item->'cost_entries') <> 3
                           OR phase6_domain_sha256(
                                'phase6-trial-allocation-evidence-v1',
                                nested_item - 'evidence_sha256'::text
                           ) IS DISTINCT FROM nested_item->>'evidence_sha256' THEN
                            RAISE EXCEPTION
                                'Phase 6 trial sample economics canonical hash mismatch';
                        END IF;
                    END LOOP;
                    SELECT COALESCE(
                        jsonb_agg(
                            jsonb_build_array(
                                sample_item->'sample_id',
                                cost_item->'scenario',
                                cost_item->'cost_entry_sha256'
                            ) ORDER BY (cost_item->>'ordinal')::integer
                        ),
                        '[]'::jsonb
                    ) INTO canonical_values
                    FROM jsonb_array_elements(
                        evidence_item->'sample_economics'
                    ) AS sample(value)
                    CROSS JOIN LATERAL (SELECT sample.value AS sample_item) AS sample_normalized
                    CROSS JOIN LATERAL jsonb_array_elements(
                        sample_item->'cost_entries'
                    ) AS cost(value)
                    CROSS JOIN LATERAL (SELECT cost.value AS cost_item) AS cost_normalized;
                    IF phase6_domain_sha256(
                            'phase6-trial-cost-ledger-set-v1',
                            canonical_values
                       ) IS DISTINCT FROM evidence_item->>'cost_set_sha256' THEN
                        RAISE EXCEPTION 'Phase 6 trial cost-set canonical hash mismatch';
                    END IF;
                    IF phase6_domain_sha256(
                            'phase6-trial-economics-v1',
                            evidence_item - 'economics_sha256'::text
                       ) IS DISTINCT FROM evidence_item->>'economics_sha256' THEN
                        RAISE EXCEPTION 'Phase 6 trial economics canonical hash mismatch';
                    END IF;
                END LOOP;
            ELSIF TG_TABLE_NAME = 'research_pipeline_snapshot_bindings' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'snapshot_id')::uuid IS DISTINCT FROM NEW.snapshot_id
                   OR NEW.payload->>'snapshot_sha256' IS DISTINCT FROM NEW.snapshot_sha256
                   OR NEW.payload->>'capability' IS DISTINCT FROM NEW.capability
                   OR NEW.payload->>'binding_sha256' IS DISTINCT FROM NEW.binding_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 snapshot-binding payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-snapshot-binding-v1',
                    NEW.payload - 'binding_sha256'::text
                );
                IF expected_hash IS DISTINCT FROM NEW.binding_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 snapshot-binding canonical hash mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_pipeline_attempts' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'phase5_trial_id')::uuid
                        IS DISTINCT FROM NEW.phase5_trial_id
                   OR NEW.payload->>'phase5_trial_key'
                        IS DISTINCT FROM NEW.phase5_trial_key
                   OR NEW.payload->>'status' IS DISTINCT FROM NEW.status
                   OR NEW.payload->>'configuration_sha256'
                        IS DISTINCT FROM NEW.config_sha256
                   OR NEW.payload->>'failure_reason' IS DISTINCT FROM NEW.failure_reason
                   OR NEW.payload->>'attempt_sha256' IS DISTINCT FROM NEW.attempt_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 attempt payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-attempt-v1',
                    NEW.payload - 'attempt_sha256'::text
                );
                IF expected_hash IS DISTINCT FROM NEW.attempt_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 attempt canonical hash mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_feature_rows' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'row_id')::uuid IS DISTINCT FROM NEW.row_id
                   OR NEW.payload->>'sample_id' IS DISTINCT FROM NEW.sample_id
                   OR NEW.payload->>'entity_id' IS DISTINCT FROM NEW.entity_id
                   OR (NEW.payload->>'decision_time_utc')::timestamptz
                        IS DISTINCT FROM NEW.decision_time_utc
                   OR NEW.payload->>'row_sha256' IS DISTINCT FROM NEW.row_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 feature-row payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-feature-row-v1',
                    NEW.payload - ARRAY['row_id','row_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM NEW.row_sha256
                   OR phase6_uuid5(
                        '5b7df50c-9da2-5f51-9b71-39187e491ce7'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.row_id THEN
                    RAISE EXCEPTION 'Phase 6 feature-row canonical identity mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_score_outputs' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'score_id')::uuid IS DISTINCT FROM NEW.score_id
                   OR NEW.payload->>'sample_id' IS DISTINCT FROM NEW.sample_id
                   OR NEW.payload->>'model_id' IS DISTINCT FROM NEW.model_id
                   OR (NEW.payload->>'research_score')::numeric
                        IS DISTINCT FROM NEW.research_score
                   OR NEW.payload->>'explanation_sha256'
                        IS DISTINCT FROM NEW.explanation_sha256
                   OR NEW.payload->>'output_sha256' IS DISTINCT FROM NEW.output_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 score-output payload mismatch';
                END IF;
                IF phase6_domain_sha256(
                        'phase6-research-explanation-v1',
                        NEW.payload->'explanation'
                   ) IS DISTINCT FROM NEW.explanation_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 score explanation canonical hash mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-score-output-v1',
                    NEW.payload - ARRAY['score_id','output_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM NEW.output_sha256
                   OR phase6_uuid5(
                        'e52726b7-d313-57d4-85f9-49c96816cf4e'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.score_id THEN
                    RAISE EXCEPTION 'Phase 6 score-output canonical identity mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_baseline_comparisons' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'comparison_id')::uuid
                        IS DISTINCT FROM NEW.comparison_id
                   OR NEW.payload->>'candidate_model_id'
                        IS DISTINCT FROM NEW.candidate_model_id
                   OR NEW.payload->>'baseline_model_id'
                        IS DISTINCT FROM NEW.baseline_model_id
                   OR NEW.payload->>'outcome' IS DISTINCT FROM NEW.outcome
                   OR NEW.payload->>'comparison_sha256'
                        IS DISTINCT FROM NEW.comparison_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 baseline-comparison payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-research-baseline-comparison-v1',
                    NEW.payload - ARRAY['comparison_id','comparison_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM NEW.comparison_sha256
                   OR phase6_uuid5(
                        '4b2f565f-b0bc-53dd-9097-da44e2cf6d88'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.comparison_id THEN
                    RAISE EXCEPTION
                        'Phase 6 baseline-comparison canonical identity mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_text_extractions' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'extraction_id')::uuid
                        IS DISTINCT FROM NEW.extraction_id
                   OR (NEW.payload->>'official_source_version_id')::uuid
                        IS DISTINCT FROM NEW.source_version_id
                   OR NEW.payload->>'document_content_sha256'
                        IS DISTINCT FROM NEW.document_sha256
                   OR NEW.payload->>'extractor_id' IS DISTINCT FROM NEW.extractor_id
                   OR NEW.payload->>'extractor_version'
                        IS DISTINCT FROM NEW.extractor_version
                   OR NEW.payload->>'model_id' IS DISTINCT FROM NEW.model_id
                   OR NEW.payload->>'prompt_version' IS DISTINCT FROM NEW.prompt_version
                   OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
                   OR NEW.payload->>'extraction_sha256'
                        IS DISTINCT FROM NEW.extraction_sha256 THEN
                    RAISE EXCEPTION 'Phase 6 text-extraction payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-text-feature-extraction-v1',
                    NEW.payload - ARRAY['extraction_id','extraction_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM NEW.extraction_sha256
                   OR phase6_uuid5(
                        'aa25921e-a1a6-59e2-ae53-424560158b4c'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.extraction_id THEN
                    RAISE EXCEPTION 'Phase 6 text-extraction canonical identity mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'research_text_corroborations' THEN
                IF (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR (NEW.payload->>'corroboration_id')::uuid
                        IS DISTINCT FROM NEW.corroboration_id
                   OR NEW.payload->>'social_attention_record_id'
                        IS DISTINCT FROM NEW.social_record_id
                   OR (NEW.payload->>'official_source_version_id')::uuid
                        IS DISTINCT FROM NEW.official_source_version_id
                   OR NEW.payload->>'official_document_sha256'
                        IS DISTINCT FROM NEW.official_document_sha256
                   OR NEW.payload->>'corroboration_sha256'
                        IS DISTINCT FROM NEW.corroboration_sha256
                   OR (NEW.payload->>'exact_match')::boolean IS DISTINCT FROM TRUE
                   OR (NEW.payload->>'contributes_standalone')::boolean
                        IS DISTINCT FROM FALSE THEN
                    RAISE EXCEPTION 'Phase 6 text-corroboration payload mismatch';
                END IF;
                expected_hash := phase6_domain_sha256(
                    'phase6-social-official-corroboration-v1',
                    NEW.payload - ARRAY['corroboration_id','corroboration_sha256']::text[]
                );
                IF expected_hash IS DISTINCT FROM NEW.corroboration_sha256
                   OR phase6_uuid5(
                        '573eeb0a-15fe-531a-9e60-e9972c535ba0'::uuid,
                        expected_hash
                   ) IS DISTINCT FROM NEW.corroboration_id THEN
                    RAISE EXCEPTION 'Phase 6 text-corroboration canonical identity mismatch';
                END IF;
            ELSE
                RAISE EXCEPTION 'Phase 6 payload validator is not bound to this table';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE6_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_05_payload_columns
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase6_payload_columns()
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_research_pipeline_run()
        RETURNS trigger AS $$
        DECLARE
            mapping_row research_mapping_versions%ROWTYPE;
            policy_row evaluation_policies%ROWTYPE;
            report_row evaluation_reports%ROWTYPE;
            outcome_row evaluation_blocked_outcomes%ROWTYPE;
        BEGIN
            SELECT * INTO mapping_row
            FROM research_mapping_versions
            WHERE id = NEW.mapping_id
            FOR KEY SHARE;
            IF NOT FOUND
               OR mapping_row.research_verdict <> 'BUILD_RESEARCH'
               OR mapping_row.canonical_family IS DISTINCT FROM NEW.canonical_family
               OR mapping_row.version_number IS DISTINCT FROM (
                    NEW.artifact_payload->>'mapping_version'
               )::integer
               OR mapping_row.mapping_input_sha256 IS DISTINCT FROM
                    NEW.artifact_payload->>'mapping_input_sha256' THEN
                RAISE EXCEPTION 'Phase 6 run requires its exact BUILD_RESEARCH mapping';
            END IF;

            SELECT * INTO policy_row
            FROM evaluation_policies
            WHERE policy_id = NEW.phase5_policy_id
              AND policy_version = NEW.phase5_policy_version
              AND policy_sha256 = NEW.phase5_policy_sha256
            FOR KEY SHARE;
            IF NOT FOUND
               OR policy_row.strategy_family IS DISTINCT FROM NEW.canonical_family THEN
                RAISE EXCEPTION 'Phase 6 run requires its exact family-matched Phase 5 policy';
            END IF;

            IF NEW.evaluation_report_id IS NOT NULL THEN
                SELECT * INTO report_row
                FROM evaluation_reports
                WHERE report_id = NEW.evaluation_report_id
                FOR KEY SHARE;
                IF NOT FOUND
                   OR report_row.mapping_id IS DISTINCT FROM NEW.mapping_id
                   OR report_row.mapping_version IS DISTINCT FROM (
                        NEW.artifact_payload->>'mapping_version'
                   )::integer
                   OR report_row.mapping_input_sha256 IS DISTINCT FROM
                        NEW.artifact_payload->>'mapping_input_sha256'
                   OR report_row.policy_id IS DISTINCT FROM NEW.phase5_policy_id
                   OR report_row.policy_version IS DISTINCT FROM NEW.phase5_policy_version
                   OR report_row.policy_sha256 IS DISTINCT FROM NEW.phase5_policy_sha256
                   OR report_row.configuration_sha256
                        IS DISTINCT FROM NEW.configuration_sha256
                   OR report_row.fixture_id IS DISTINCT FROM NEW.phase5_fixture_id
                   OR report_row.fixture_sha256 IS DISTINCT FROM NEW.phase5_fixture_sha256
                   OR report_row.snapshot_bundle_sha256
                         IS DISTINCT FROM NEW.snapshot_bundle_sha256
                   OR report_row.git_sha IS DISTINCT FROM
                        NEW.artifact_payload->>'code_version_git_sha'
                   OR report_row.random_seed IS DISTINCT FROM (
                        NEW.artifact_payload->>'random_seed'
                   )::bigint
                   OR NEW.artifact_payload#>>'{phase5_evaluation,evaluation_report_sha256}'
                        IS DISTINCT FROM report_row.report_sha256
                   OR (
                        NEW.artifact_payload#>>'{phase5_evaluation,raw_trial_count}'
                   )::integer IS DISTINCT FROM report_row.raw_trial_count
                   OR (
                        NEW.artifact_payload#>>'{phase5_evaluation,effective_trial_count}'
                   )::numeric IS DISTINCT FROM report_row.effective_trial_count
                   OR report_row.state IS DISTINCT FROM NEW.promotion_state
                   OR NOT report_row.synthetic
                   OR NOT report_row.no_real_performance_claim THEN
                    RAISE EXCEPTION 'Phase 6 run Phase 5 report lineage mismatch';
                END IF;
            ELSE
                SELECT * INTO outcome_row
                FROM evaluation_blocked_outcomes
                WHERE outcome_id = NEW.evaluation_outcome_id
                FOR KEY SHARE;
                IF NOT FOUND
                   OR outcome_row.mapping_id IS DISTINCT FROM NEW.mapping_id
                   OR outcome_row.policy_id IS DISTINCT FROM NEW.phase5_policy_id
                   OR outcome_row.policy_version IS DISTINCT FROM NEW.phase5_policy_version
                   OR outcome_row.resolved_policy_sha256
                        IS DISTINCT FROM NEW.phase5_policy_sha256
                   OR outcome_row.fixture_id IS DISTINCT FROM NEW.phase5_fixture_id
                   OR outcome_row.resolved_fixture_sha256
                         IS DISTINCT FROM NEW.phase5_fixture_sha256
                   OR (
                        outcome_row.git_sha IS NOT NULL
                        AND outcome_row.git_sha IS DISTINCT FROM
                            NEW.artifact_payload->>'code_version_git_sha'
                   )
                   OR (
                        outcome_row.resolved_fixture_random_seed IS NOT NULL
                        AND outcome_row.resolved_fixture_random_seed IS DISTINCT FROM (
                            NEW.artifact_payload->>'random_seed'
                        )::bigint
                   )
                   OR NEW.artifact_payload#>>'{phase5_evaluation,evaluation_report_sha256}'
                        IS NOT NULL
                   OR (
                        NEW.artifact_payload#>>'{phase5_evaluation,raw_trial_count}'
                   )::bigint IS DISTINCT FROM outcome_row.resolved_raw_trial_count
                   OR outcome_row.state IS DISTINCT FROM NEW.promotion_state
                   OR NOT outcome_row.synthetic
                   OR NOT outcome_row.no_real_performance_claim THEN
                    RAISE EXCEPTION 'Phase 6 run Phase 5 blocked-outcome lineage mismatch';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_pipeline_runs_10_lineage
        BEFORE INSERT ON research_pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_research_pipeline_run()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_snapshot_binding()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
            snapshot_row data_snapshots%ROWTYPE;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.run_id
            FOR KEY SHARE;
            SELECT * INTO snapshot_row
            FROM data_snapshots
            WHERE snapshot_id = NEW.snapshot_id
            FOR KEY SHARE;
            IF NOT FOUND
               OR snapshot_row.snapshot_sha256 IS DISTINCT FROM NEW.snapshot_sha256
               OR snapshot_row.capability IS DISTINCT FROM NEW.capability
               OR snapshot_row.mapping_id IS DISTINCT FROM run_row.mapping_id
               OR snapshot_row.canonical_family IS DISTINCT FROM run_row.canonical_family
               OR snapshot_row.verdict <> 'BUILD_RESEARCH' THEN
                RAISE EXCEPTION 'Phase 6 snapshot binding lineage mismatch';
            END IF;

            IF run_row.evaluation_report_id IS NOT NULL
               AND NOT EXISTS (
                    SELECT 1
                    FROM evaluation_report_snapshots
                    WHERE report_id = run_row.evaluation_report_id
                      AND snapshot_id = NEW.snapshot_id
                      AND snapshot_sha256 = NEW.snapshot_sha256
                      AND capability = NEW.capability
               ) THEN
                RAISE EXCEPTION 'Phase 6 snapshot is absent from the Phase 5 report';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_pipeline_snapshot_bindings_10_lineage
        BEFORE INSERT ON research_pipeline_snapshot_bindings
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_snapshot_binding()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_attempt()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
            trial_row evaluation_trials%ROWTYPE;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.run_id
            FOR KEY SHARE;
            IF run_row.evaluation_report_id IS NULL THEN
                IF NEW.phase5_report_id IS NOT NULL
                   OR NEW.phase5_trial_id IS NOT NULL
                   OR NEW.phase5_trial_key IS NOT NULL
                   OR NEW.status <> 'blocked' THEN
                    RAISE EXCEPTION 'Phase 6 blocked run cannot claim a Phase 5 trial';
                END IF;
                RETURN NEW;
            END IF;

            IF NEW.phase5_report_id IS NULL OR NEW.phase5_trial_id IS NULL THEN
                RAISE EXCEPTION 'Phase 6 attempt requires its Phase 5 trial';
            END IF;
            IF NEW.phase5_report_id IS DISTINCT FROM run_row.evaluation_report_id THEN
                RAISE EXCEPTION 'Phase 6 attempt Phase 5 trial lineage mismatch';
            END IF;
            SELECT * INTO trial_row
            FROM evaluation_trials
            WHERE report_id = NEW.phase5_report_id
              AND trial_id = NEW.phase5_trial_id
            FOR KEY SHARE;
            IF NOT FOUND
               OR trial_row.config_sha256 IS DISTINCT FROM NEW.config_sha256
               OR trial_row.trial_key IS DISTINCT FROM NEW.phase5_trial_key
               OR trial_row.status IS DISTINCT FROM NEW.status THEN
                RAISE EXCEPTION 'Phase 6 attempt Phase 5 trial lineage mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_pipeline_attempts_10_lineage
        BEFORE INSERT ON research_pipeline_attempts
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_attempt()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_text_extraction()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
            source_authority_value text;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.run_id
            FOR KEY SHARE;
            SELECT source_authority INTO source_authority_value
            FROM research_source_versions
            WHERE id = NEW.source_version_id
            FOR KEY SHARE;
            IF run_row.canonical_family <> 'C_OFFICIAL_EVENT_TEXT_OVERLAY'
               OR source_authority_value NOT IN ('official','news') THEN
                RAISE EXCEPTION 'Phase 6 text extraction requires official or licensed-news input';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM research_pipeline_snapshot_bindings AS binding
                JOIN data_normalized_observations AS observation
                  ON observation.snapshot_id = binding.snapshot_id
                WHERE binding.run_id = NEW.run_id
                  AND binding.capability = 'official_document_event_metadata'
                  AND observation.payload->>'record_type' = 'official_document_content'
                  AND observation.payload->>'official_source_version_id'
                        = NEW.source_version_id::text
                  AND observation.payload->>'official_document_id'
                        = NEW.payload->>'official_document_id'
                  AND observation.payload->>'document_content_sha256'
                        = NEW.document_sha256
                  AND observation.available_at = (
                        NEW.payload->>'available_at_utc'
                      )::timestamptz
                  AND (observation.payload->>'corrected_at')::timestamptz
                        IS NOT DISTINCT FROM (
                            NEW.payload->>'corrected_at_utc'
                        )::timestamptz
                  AND (observation.payload->>'correction_sequence')::integer
                        = (NEW.payload->>'correction_sequence')::integer
                  AND observation.available_at <= run_row.created_at_utc
            ) THEN
                RAISE EXCEPTION 'Phase 6 text extraction lacks exact immutable document lineage';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_text_extractions_10_lineage
        BEFORE INSERT ON research_text_extractions
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_text_extraction()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase6_text_corroboration()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
            official_authority text;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.run_id
            FOR KEY SHARE;
            SELECT source_authority INTO official_authority
            FROM research_source_versions
            WHERE id = NEW.official_source_version_id
            FOR KEY SHARE;
            IF run_row.canonical_family <> 'C_OFFICIAL_EVENT_TEXT_OVERLAY'
               OR official_authority IS DISTINCT FROM 'official'
               OR NOT EXISTS (
                    SELECT 1
                    FROM mapping_official_corroborations
                    WHERE mapping_id = run_row.mapping_id
                      AND official_source_version_id = NEW.official_source_version_id
               )
               OR NOT EXISTS (
                    SELECT 1
                    FROM research_text_extractions
                    WHERE run_id = NEW.run_id
                      AND source_version_id = NEW.official_source_version_id
                      AND document_sha256 = NEW.official_document_sha256
               )
               OR NOT EXISTS (
                    SELECT 1
                    FROM research_pipeline_snapshot_bindings AS binding
                    JOIN data_normalized_observations AS social
                      ON social.snapshot_id = binding.snapshot_id
                    JOIN data_normalized_observations AS official
                      ON official.snapshot_id = binding.snapshot_id
                    WHERE binding.run_id = NEW.run_id
                      AND binding.capability = 'official_document_event_metadata'
                      AND social.payload->>'record_type' = 'social_attention'
                      AND social.payload->>'social_attention_record_id' = NEW.social_record_id
                      AND social.payload->>'claimed_official_source_version_id'
                            = NEW.official_source_version_id::text
                      AND (social.payload->>'manipulation_prone')::boolean IS TRUE
                      AND (social.payload->>'contributes_standalone')::boolean IS FALSE
                      AND NEW.payload#>>'{social_source_reference,capability}'
                            = 'official_document_event_metadata'
                      AND NEW.payload#>>'{social_source_reference,record_type}'
                            = 'social_attention'
                      AND social.snapshot_id::text
                            = NEW.payload#>>'{social_source_reference,snapshot_id}'
                      AND social.snapshot_sha256
                            = NEW.payload#>>'{social_source_reference,snapshot_sha256}'
                      AND social.raw_observation_id::text
                            = NEW.payload#>>'{social_source_reference,raw_observation_id}'
                      AND social.observation_revision_id::text
                            = NEW.payload#>>'{social_source_reference,observation_revision_id}'
                      AND social.normalized_observation_id::text
                            = NEW.payload#>>'{social_source_reference,normalized_observation_id}'
                      AND social.raw_payload_sha256
                            = NEW.payload#>>'{social_source_reference,raw_payload_sha256}'
                      AND social.normalized_content_sha256
                            = NEW.payload#>>'{social_source_reference,normalized_content_sha256}'
                      AND social.source_record_id
                            = NEW.payload#>>'{social_source_reference,source_record_id}'
                      AND social.available_at = (
                            NEW.payload#>>'{social_source_reference,available_at_utc}'
                          )::timestamptz
                      AND social.valid_from = (
                            NEW.payload#>>'{social_source_reference,valid_from_utc}'
                          )::timestamptz
                      AND social.valid_to IS NOT DISTINCT FROM (
                            NEW.payload#>>'{social_source_reference,valid_to_utc}'
                          )::timestamptz
                      AND social.instrument_id IS NOT DISTINCT FROM (
                            NEW.payload#>>'{social_source_reference,instrument_id}'
                          )::uuid
                      AND social.listing_id IS NOT DISTINCT FROM (
                            NEW.payload#>>'{social_source_reference,listing_id}'
                          )::uuid
                      AND official.payload->>'record_type' = 'official_document_content'
                      AND official.payload->>'official_source_version_id'
                            = NEW.official_source_version_id::text
                      AND official.payload->>'document_content_sha256'
                            = NEW.official_document_sha256
                      AND NEW.payload#>>'{official_source_reference,capability}'
                            = 'official_document_event_metadata'
                      AND NEW.payload#>>'{official_source_reference,record_type}'
                            = 'official_document_content'
                      AND official.snapshot_id::text
                            = NEW.payload#>>'{official_source_reference,snapshot_id}'
                      AND official.snapshot_sha256
                            = NEW.payload#>>'{official_source_reference,snapshot_sha256}'
                      AND official.raw_observation_id::text
                            = NEW.payload#>>'{official_source_reference,raw_observation_id}'
                      AND official.observation_revision_id::text
                            = NEW.payload#>>'{official_source_reference,observation_revision_id}'
                      AND official.normalized_observation_id::text
                            = NEW.payload#>>'{official_source_reference,normalized_observation_id}'
                      AND official.raw_payload_sha256
                            = NEW.payload#>>'{official_source_reference,raw_payload_sha256}'
                      AND official.normalized_content_sha256
                            = NEW.payload#>>'{official_source_reference,normalized_content_sha256}'
                      AND official.source_record_id
                            = NEW.payload#>>'{official_source_reference,source_record_id}'
                      AND official.available_at = (
                            NEW.payload#>>'{official_source_reference,available_at_utc}'
                          )::timestamptz
                      AND official.valid_from = (
                            NEW.payload#>>'{official_source_reference,valid_from_utc}'
                          )::timestamptz
                      AND official.valid_to IS NOT DISTINCT FROM (
                            NEW.payload#>>'{official_source_reference,valid_to_utc}'
                          )::timestamptz
                      AND official.instrument_id IS NOT DISTINCT FROM (
                            NEW.payload#>>'{official_source_reference,instrument_id}'
                          )::uuid
                      AND official.listing_id IS NOT DISTINCT FROM (
                            NEW.payload#>>'{official_source_reference,listing_id}'
                          )::uuid
                      AND official.available_at <= social.available_at
                      AND social.available_at <= run_row.created_at_utc
                      AND official.instrument_id IS NOT DISTINCT FROM social.instrument_id
                      AND official.listing_id IS NOT DISTINCT FROM social.listing_id
               ) THEN
                RAISE EXCEPTION 'Phase 6 social attention requires exact official corroboration';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_text_corroborations_10_lineage
        BEFORE INSERT ON research_text_corroborations
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_text_corroboration()
        """
    )

    op.execute(
        """
        CREATE FUNCTION phase6_registry_matches_artifact(
            checked_table regclass,
            checked_run_id uuid,
            expected_payloads jsonb
        ) RETURNS boolean AS $$
        DECLARE
            expected_count integer;
            actual_count bigint;
            minimum_ordinal integer;
            maximum_ordinal integer;
            actual_payloads jsonb;
        BEGIN
            IF jsonb_typeof(expected_payloads) IS DISTINCT FROM 'array' THEN
                RETURN FALSE;
            END IF;
            expected_count := jsonb_array_length(expected_payloads);
            EXECUTE format(
                'SELECT count(*), min(ordinal), max(ordinal), '
                'COALESCE(jsonb_agg(payload ORDER BY ordinal), ''[]''::jsonb) '
                'FROM %s WHERE run_id = $1',
                checked_table
            ) INTO actual_count, minimum_ordinal, maximum_ordinal, actual_payloads
              USING checked_run_id;
            RETURN actual_count = expected_count
                AND (
                    (expected_count = 0
                     AND minimum_ordinal IS NULL
                     AND maximum_ordinal IS NULL)
                    OR (
                        expected_count > 0
                        AND minimum_ordinal = 1
                        AND maximum_ordinal = expected_count
                    )
                )
                AND actual_payloads IS NOT DISTINCT FROM expected_payloads;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase6_run_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_run_id uuid;
            run_row research_pipeline_runs%ROWTYPE;
            expected_extractions jsonb;
            expected_corroborations jsonb;
            actual_attempt_count bigint;
            actual_gate_codes jsonb;
            actual_trial_set_sha256 text;
        BEGIN
            IF TG_TABLE_NAME = 'research_pipeline_runs' THEN
                checked_run_id := NEW.id;
            ELSE
                checked_run_id := NEW.run_id;
            END IF;

            -- A newly inserted root already has its own deferred completeness
            -- event.  Every child row is inserted in the same transaction, so
            -- that root event observes the final transaction state and can
            -- validate the complete artifact exactly once.  Child-only writes
            -- against an existing root do not match xmin and still run the
            -- full validator, which keeps append-only completeness fail closed.
            IF TG_TABLE_NAME <> 'research_pipeline_runs'
               AND EXISTS (
                    SELECT 1
                    FROM research_pipeline_runs AS current_run
                    WHERE current_run.id = checked_run_id
                      AND current_run.xmin = pg_current_xact_id()::xid
               ) THEN
                RETURN NEW;
            END IF;

            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = checked_run_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 6 research run completeness target is missing';
            END IF;

            IF run_row.canonical_family = 'C_OFFICIAL_EVENT_TEXT_OVERLAY' THEN
                expected_extractions :=
                    run_row.artifact_payload#>'{family_evidence,extractions}';
                expected_corroborations :=
                    run_row.artifact_payload#>'{family_evidence,corroborations}';
                IF jsonb_typeof(expected_extractions) IS DISTINCT FROM 'array'
                   OR jsonb_typeof(expected_corroborations) IS DISTINCT FROM 'array' THEN
                    RAISE EXCEPTION
                        'Phase 6 research run has incomplete child registries';
                END IF;
            ELSE
                IF run_row.artifact_payload#>'{family_evidence,extractions}' IS NOT NULL
                   OR run_row.artifact_payload#>'{family_evidence,corroborations}' IS NOT NULL THEN
                    RAISE EXCEPTION
                        'Phase 6 non-text run cannot claim text child registries';
                END IF;
                expected_extractions := '[]'::jsonb;
                expected_corroborations := '[]'::jsonb;
            END IF;

            IF run_row.evaluation_report_id IS NOT NULL THEN
                SELECT count(*) INTO actual_attempt_count
                FROM research_pipeline_attempts
                WHERE run_id = checked_run_id;
                SELECT phase6_domain_sha256(
                    'phase6-phase5-trial-set-v1',
                    COALESCE(
                        jsonb_agg(
                            jsonb_build_array(
                                trial_id::text,
                                trial_key,
                                status,
                                config_sha256
                            ) ORDER BY trial_id::text, trial_key
                        ),
                        '[]'::jsonb
                    )
                ) INTO actual_trial_set_sha256
                FROM evaluation_trials
                WHERE report_id = run_row.evaluation_report_id;
                SELECT COALESCE(
                    jsonb_agg(to_jsonb(gate_code) ORDER BY ordinal),
                    '[]'::jsonb
                ) INTO actual_gate_codes
                FROM evaluation_gate_results
                WHERE report_id = run_row.evaluation_report_id;
                IF actual_attempt_count IS DISTINCT FROM (
                       run_row.artifact_payload#>>'{phase5_evaluation,raw_trial_count}'
                   )::bigint
                   OR actual_trial_set_sha256 IS DISTINCT FROM
                        run_row.artifact_payload#>>
                            '{phase5_evaluation,phase5_trial_set_sha256}'
                   OR actual_gate_codes IS DISTINCT FROM
                        run_row.artifact_payload#>'{phase5_evaluation,gate_codes}'
                   OR EXISTS (
                        (SELECT trial_id, trial_key, status, config_sha256
                         FROM evaluation_trials
                         WHERE report_id = run_row.evaluation_report_id)
                        EXCEPT
                        (SELECT phase5_trial_id, phase5_trial_key, status, config_sha256
                         FROM research_pipeline_attempts
                         WHERE run_id = checked_run_id)
                   )
                   OR EXISTS (
                        (SELECT phase5_trial_id, phase5_trial_key, status, config_sha256
                         FROM research_pipeline_attempts
                         WHERE run_id = checked_run_id)
                        EXCEPT
                        (SELECT trial_id, trial_key, status, config_sha256
                         FROM evaluation_trials
                         WHERE report_id = run_row.evaluation_report_id)
                   )
                   OR EXISTS (
                        SELECT 1
                        FROM evaluation_trials AS trial
                        WHERE trial.report_id = run_row.evaluation_report_id
                          AND trial.configuration->>'phase6_pipeline_input_sha256'
                                IS DISTINCT FROM
                                    run_row.artifact_payload->>'pipeline_input_sha256'
                   )
                   OR EXISTS (
                        SELECT 1
                        FROM evaluation_trials AS trial
                        LEFT JOIN LATERAL (
                            SELECT value
                            FROM jsonb_array_elements(
                                run_row.artifact_payload->'model_output_sets'
                            ) AS output(value)
                            WHERE value->>'trial_key' = trial.trial_key
                        ) AS output_set ON TRUE
                        LEFT JOIN LATERAL (
                            SELECT value
                            FROM jsonb_array_elements(
                                run_row.artifact_payload->'trial_economics'
                            ) AS economics(value)
                            WHERE value->>'trial_key' = trial.trial_key
                        ) AS economics ON TRUE
                        WHERE trial.report_id = run_row.evaluation_report_id
                          AND trial.status = 'completed'
                          AND (
                            output_set.value IS NULL
                            OR economics.value IS NULL
                            OR trial.configuration->>'model'
                                IS DISTINCT FROM output_set.value->>'model_id'
                            OR trial.configuration->>'phase6_model_output_sha256'
                                IS DISTINCT FROM
                                    output_set.value->>'model_output_sha256'
                            OR trial.configuration->>'phase6_output_set_sha256'
                                IS DISTINCT FROM output_set.value->>'output_set_sha256'
                            OR trial.configuration->>'phase6_output_set_sha256'
                                IS DISTINCT FROM economics.value->>'output_set_sha256'
                            OR trial.configuration->>'phase6_trial_cost_set_sha256'
                                IS DISTINCT FROM economics.value->>'cost_set_sha256'
                            OR trial.configuration->>'phase6_payoff_formula_id'
                                IS DISTINCT FROM
                                    'phase6-long-flat-weight-times-label-quantized-v1'
                            OR trial.configuration->>'phase6_ledger_cell_set_sha256'
                                IS DISTINCT FROM (
                                    SELECT phase6_domain_sha256(
                                        'phase6-phase5-ledger-cell-set-v2',
                                        COALESCE(
                                            jsonb_agg(
                                                jsonb_build_array(
                                                    cell.value->'cell_id',
                                                    cell.value->'cell_sha256'
                                                ) ORDER BY (
                                                    cell.value->>'ordinal'
                                                )::integer
                                            ),
                                            '[]'::jsonb
                                        )
                                    )
                                    FROM jsonb_array_elements(
                                        output_set.value->'ledger_cells'
                                    ) AS cell(value)
                                )
                          )
                   )
                   OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements(
                            run_row.artifact_payload->'model_output_sets'
                        ) AS output(value)
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM evaluation_trials AS trial
                            WHERE trial.report_id = run_row.evaluation_report_id
                              AND trial.status = 'completed'
                              AND trial.trial_key = output.value->>'trial_key'
                        )
                   ) THEN
                    RAISE EXCEPTION
                        'Phase 6 Phase 5 trial, gate, and research-ledger lineage mismatch';
                END IF;
            END IF;

            IF NOT phase6_registry_matches_artifact(
                    'research_pipeline_snapshot_bindings'::regclass,
                    checked_run_id,
                    run_row.artifact_payload->'snapshot_bindings'
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_pipeline_attempts'::regclass,
                    checked_run_id,
                    run_row.artifact_payload->'attempts'
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_feature_rows'::regclass,
                    checked_run_id,
                    run_row.artifact_payload->'feature_rows'
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_score_outputs'::regclass,
                    checked_run_id,
                    run_row.artifact_payload->'scores'
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_baseline_comparisons'::regclass,
                    checked_run_id,
                    run_row.artifact_payload->'baseline_comparisons'
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_text_extractions'::regclass,
                    checked_run_id,
                    expected_extractions
               )
               OR NOT phase6_registry_matches_artifact(
                    'research_text_corroborations'::regclass,
                    checked_run_id,
                    expected_corroborations
               ) THEN
                RAISE EXCEPTION 'Phase 6 research run has incomplete child registries';
            END IF;

            IF EXISTS (
                WITH RECURSIVE artifact_nodes(value) AS (
                    SELECT run_row.artifact_payload
                    UNION ALL
                    SELECT child.value
                    FROM artifact_nodes AS parent
                    CROSS JOIN LATERAL (
                        SELECT object_item.value
                        FROM jsonb_each(
                            CASE
                                WHEN jsonb_typeof(parent.value) = 'object'
                                    THEN parent.value
                                ELSE '{}'::jsonb
                            END
                        ) AS object_item(key, value)
                        UNION ALL
                        SELECT array_item.value
                        FROM jsonb_array_elements(
                            CASE
                                WHEN jsonb_typeof(parent.value) = 'array'
                                    THEN parent.value
                                ELSE '[]'::jsonb
                            END
                        ) AS array_item(value)
                    ) AS child(value)
                )
                SELECT 1
                FROM artifact_nodes AS reference
                WHERE jsonb_typeof(reference.value) = 'object'
                  AND reference.value ?& ARRAY[
                    'capability','snapshot_id','snapshot_sha256',
                    'raw_observation_id','observation_revision_id',
                    'normalized_observation_id','raw_payload_sha256',
                    'normalized_content_sha256','record_type','source_record_id',
                    'instrument_id','listing_id','available_at_utc','valid_from_utc',
                    'valid_to_utc'
                  ]
                  AND NOT EXISTS (
                    SELECT 1
                    FROM research_pipeline_snapshot_bindings AS binding
                    JOIN data_normalized_observations AS observation
                      ON observation.snapshot_id = binding.snapshot_id
                    WHERE binding.run_id = checked_run_id
                      AND binding.capability = reference.value->>'capability'
                      AND binding.snapshot_id = (
                            reference.value->>'snapshot_id'
                          )::uuid
                      AND binding.snapshot_sha256 =
                            reference.value->>'snapshot_sha256'
                      AND observation.raw_observation_id = (
                            reference.value->>'raw_observation_id'
                          )::uuid
                      AND observation.observation_revision_id = (
                            reference.value->>'observation_revision_id'
                          )::uuid
                      AND observation.normalized_observation_id = (
                            reference.value->>'normalized_observation_id'
                          )::uuid
                      AND observation.raw_payload_sha256 =
                            reference.value->>'raw_payload_sha256'
                      AND observation.normalized_content_sha256 =
                            reference.value->>'normalized_content_sha256'
                      AND observation.payload->>'record_type' =
                            reference.value->>'record_type'
                      AND observation.source_record_id =
                            reference.value->>'source_record_id'
                      AND observation.instrument_id IS NOT DISTINCT FROM (
                            reference.value->>'instrument_id'
                          )::uuid
                      AND observation.listing_id IS NOT DISTINCT FROM (
                            reference.value->>'listing_id'
                          )::uuid
                      AND observation.available_at = (
                            reference.value->>'available_at_utc'
                          )::timestamptz
                      AND observation.valid_from = (
                            reference.value->>'valid_from_utc'
                          )::timestamptz
                      AND observation.valid_to IS NOT DISTINCT FROM (
                            reference.value->>'valid_to_utc'
                          )::timestamptz
                  )
            ) THEN
                RAISE EXCEPTION
                    'Phase 6 artifact source reference lineage mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER research_pipeline_runs_complete
        AFTER INSERT ON research_pipeline_runs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase6_run_completeness()
        """
    )
    for table in PHASE6_CHILD_TABLES:
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {table}_run_complete
            AFTER INSERT ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION validate_phase6_run_completeness()
            """
        )

    op.execute(
        """
        CREATE FUNCTION reject_phase6_research_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 6 research artifacts are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE6_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase6_research_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase6_research_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE6_CHILD_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_run_complete ON {table}")
    op.execute("DROP TRIGGER IF EXISTS research_pipeline_runs_complete ON research_pipeline_runs")
    op.execute(
        "DROP TRIGGER IF EXISTS research_text_corroborations_10_lineage "
        "ON research_text_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_text_extractions_10_lineage ON research_text_extractions"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_pipeline_attempts_10_lineage ON research_pipeline_attempts"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_pipeline_snapshot_bindings_10_lineage "
        "ON research_pipeline_snapshot_bindings"
    )
    op.execute("DROP TRIGGER IF EXISTS research_pipeline_runs_10_lineage ON research_pipeline_runs")
    for table in reversed(PHASE6_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_05_payload_columns ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_00_created_at_utc ON {table}")
    for table in reversed(PHASE6_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")

    op.execute("DROP FUNCTION IF EXISTS reject_phase6_research_mutation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_run_completeness()")
    op.execute("DROP FUNCTION IF EXISTS phase6_registry_matches_artifact(regclass, uuid, jsonb)")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_text_corroboration()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_text_extraction()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_attempt()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_snapshot_binding()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_research_pipeline_run()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase6_payload_columns()")
    op.execute("DROP FUNCTION IF EXISTS own_phase6_created_at_utc()")
    op.execute("DROP FUNCTION IF EXISTS phase6_uuid5(uuid, text)")
    op.execute("DROP FUNCTION IF EXISTS phase6_sha1(bytea)")
    op.execute("DROP FUNCTION IF EXISTS phase6_domain_sha256(text, jsonb)")
    op.execute("DROP FUNCTION IF EXISTS phase6_canonical_json(jsonb)")

    op.execute("DROP FUNCTION validate_phase5_report_source_lineage(uuid)")
    op.execute(
        "ALTER FUNCTION validate_phase5_report_source_lineage_phase5_base(uuid) "
        "RENAME TO validate_phase5_report_source_lineage"
    )
    op.execute("DROP FUNCTION phase6_sha256_prefix64_fraction(text)")
    op.execute("DROP FUNCTION phase6_source_payload_equivalent(text, jsonb, jsonb)")

    op.drop_table("research_text_corroborations")
    op.drop_table("research_text_extractions")
    op.drop_table("research_baseline_comparisons")
    op.drop_table("research_score_outputs")
    op.drop_table("research_feature_rows")
    op.drop_table("research_pipeline_attempts")
    op.drop_table("research_pipeline_snapshot_bindings")
    op.drop_index(
        "ix_research_pipeline_runs_family_created",
        table_name="research_pipeline_runs",
    )
    op.drop_table("research_pipeline_runs")

    # Never erase Phase 4 observations in order to make a downgrade appear to
    # succeed. An operator must remain on Phase 6 while additive record types
    # exist, preserving immutable evidence and the prior-row byte contract.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM data_snapshots
                WHERE fixture_set_version IN (
                    'phase6-synthetic-pit-fixtures-v1',
                    'phase6-synthetic-pit-fixtures-v2'
                )
            ) OR EXISTS (
                SELECT 1 FROM data_quality_findings
                WHERE rule_set_version IN (
                    'phase6-data-contract-quality-v1',
                    'phase6-data-contract-quality-v2'
                )
                   OR code IN (
                        'pit_classification_invalid',
                        'document_content_hash_mismatch',
                        'document_correction_timing_invalid',
                        'official_corroboration_mismatch'
                   )
            ) OR EXISTS (
                SELECT 1 FROM data_normalized_observations
                WHERE payload->>'record_type' IN (
                    'sector_classification','official_document_content','social_attention',
                    'macro_rate_observation','crisis_window_definition'
                )
            ) OR EXISTS (
                SELECT 1 FROM data_snapshot_constituents
                WHERE record_type IN (
                    'sector_classification','official_document_content','social_attention',
                    'macro_rate_observation','crisis_window_definition'
                )
            ) OR EXISTS (
                SELECT 1 FROM data_quality_findings
                WHERE affected_record_type IN (
                    'sector_classification','official_document_content','social_attention',
                    'macro_rate_observation','crisis_window_definition'
                )
            ) THEN
                RAISE EXCEPTION
                    'Phase 6 downgrade blocked by additive Phase 4 record types';
            END IF;
        END
        $$
        """
    )

    op.drop_constraint(
        "ck_data_snapshot_capability",
        "data_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_capability",
        "data_snapshots",
        _phase4_snapshot_capability_constraint(extended=False),
    )
    op.drop_constraint(
        "ck_data_snapshot_frozen_versions",
        "data_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_frozen_versions",
        "data_snapshots",
        _phase4_snapshot_frozen_versions_constraint(extended=False),
    )
    op.drop_constraint(
        "ck_data_quality_finding_identities",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_identities",
        "data_quality_findings",
        _phase4_quality_finding_identity_constraint(extended=False),
    )
    op.drop_constraint(
        "ck_data_quality_finding_code",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_code",
        "data_quality_findings",
        _phase4_quality_finding_code_constraint(extended=False),
    )
    op.drop_constraint(
        "ck_data_snapshot_constituent_record_type",
        "data_snapshot_constituents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_snapshot_constituent_record_type",
        "data_snapshot_constituents",
        f"record_type IN ({_phase4_record_type_constraint(extended=False)})",
    )
    op.drop_constraint(
        "ck_data_quality_finding_record_type",
        "data_quality_findings",
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_quality_finding_record_type",
        "data_quality_findings",
        "affected_record_type IS NULL OR affected_record_type IN ("
        f"{_phase4_record_type_constraint(extended=False)})",
    )
    op.execute(_phase4_record_type_function(extended=False))
    op.execute(_phase4_snapshot_request_function(extended=False))
    op.execute(_phase4_normalized_identity_scope_bridge_sql(extended=False))
