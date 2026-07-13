from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from fable5_extraction.models import TradingIdeaCard
from pydantic import ValidationError
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError

from fable5_mapping.mapper import map_idea
from fable5_mapping.models import (
    MappingDecision,
    MappingInput,
    MappingRationale,
    MappingWithRationale,
    ResearchMapping,
)
from fable5_mapping.rationale import build_mapping_rationale
from fable5_mapping.rules import CURRENT_RULE_SET, MappingRuleSet, canonical_sha256


class MappingNotFoundError(LookupError):
    pass


class MappingLineageError(ValueError):
    pass


class MappingConflictError(ValueError):
    pass


class MappingRepository:
    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _mapping_corroborations(connection: Connection, mapping_id: UUID) -> tuple[UUID, ...]:
        values = connection.execute(
            text(
                "SELECT official_source_version_id "
                "FROM mapping_official_corroborations "
                "WHERE mapping_id = :mapping_id ORDER BY official_source_version_id"
            ),
            {"mapping_id": mapping_id},
        ).scalars()
        return tuple(values)

    @classmethod
    def _mapping_from_row(cls, connection: Connection, row: RowMapping) -> ResearchMapping:
        return ResearchMapping(
            mapping_id=row["id"],
            mapping_version=row["version_number"],
            card_id=row["card_id"],
            card_sha256=row["card_sha256"],
            mapping_input_sha256=row["mapping_input_sha256"],
            extraction_request_id=row["extraction_request_id"],
            extraction_request_fingerprint=row["request_fingerprint"],
            source_id=row["source_id"],
            source_version_id=row["source_version_id"],
            source_version=row["source_version_number"],
            source_content_sha256=row["source_content_sha256"],
            official_corroboration_source_version_ids=cls._mapping_corroborations(
                connection, row["id"]
            ),
            extractor_kind=row["extractor_kind"],
            extractor_id=row["extractor_id"],
            extractor_version=row["extractor_version"],
            extraction_model_id=row["extraction_model_id"],
            extraction_model_revision=row["extraction_model_revision"],
            extraction_prompt_version=row["extraction_prompt_version"],
            extraction_prompt_sha256=row["extraction_prompt_sha256"],
            extraction_schema_version=row["extraction_schema_version"],
            extraction_config_sha256=row["extraction_config_sha256"],
            canonical_family=row["canonical_family"],
            verdict=row["research_verdict"],
            matched_rule_ids=row["matched_rule_ids"],
            reason_codes=row["reason_codes"],
            mapper_rule_set_version=row["mapper_rule_set_version"],
            mapper_rule_set_sha256=row["mapper_rule_set_sha256"],
            source_evidence=row["source_evidence"],
            rationale_template_version=row["rationale_template_version"],
            created_at_utc=row["created_at_utc"],
        )

    @staticmethod
    def _rationale_from_row(row: RowMapping) -> MappingRationale:
        return MappingRationale(
            rationale_id=row["id"],
            mapping_id=row["mapping_id"],
            template_version=row["template_version"],
            markdown=row["markdown_content"],
            content_sha256=row["content_sha256"],
            created_at_utc=row["created_at_utc"],
        )

    @classmethod
    def _bundle_from_mapping_row(
        cls, connection: Connection, row: RowMapping
    ) -> MappingWithRationale:
        mapping = cls._mapping_from_row(connection, row)
        rationale_row = (
            connection.execute(
                text("SELECT * FROM mapping_rationale_artifacts WHERE mapping_id = :mapping_id"),
                {"mapping_id": mapping.mapping_id},
            )
            .mappings()
            .one_or_none()
        )
        if rationale_row is None:
            raise MappingLineageError("persisted mapping is missing its immutable rationale")
        return MappingWithRationale(
            mapping=mapping,
            rationale=cls._rationale_from_row(rationale_row),
        )

    @staticmethod
    def _card_corroborations(
        connection: Connection, card_id: UUID
    ) -> tuple[tuple[UUID, UUID], ...]:
        rows = connection.execute(
            text(
                "SELECT c.official_source_version_id, v.source_id, v.source_authority "
                "FROM card_official_corroborations AS c "
                "JOIN research_source_versions AS v "
                "ON v.id = c.official_source_version_id "
                "WHERE c.card_id = :card_id ORDER BY c.official_source_version_id"
            ),
            {"card_id": card_id},
        ).mappings()
        result: list[tuple[UUID, UUID]] = []
        for row in rows:
            if row["source_authority"] != "official":
                raise MappingLineageError("persisted corroboration is not an official source")
            result.append((row["official_source_version_id"], row["source_id"]))
        return tuple(result)

    @staticmethod
    def _assert_equal(actual: object, expected: object, field: str) -> None:
        if actual != expected:
            raise MappingLineageError(f"persisted mapping lineage mismatch for {field}")

    @classmethod
    def _load_mapping_input(
        cls,
        connection: Connection,
        card_id: UUID,
        *,
        lock_card: bool = True,
    ) -> MappingInput:
        query = """
                    SELECT
                        c.id AS card_id,
                        c.extraction_request_id AS card_extraction_request_id,
                        c.testability_status AS card_testability_status,
                        c.testability_score AS card_testability_score,
                        c.infra_risk AS card_infra_risk,
                        c.corroboration_status AS card_corroboration_status,
                        c.contribution_status AS card_contribution_status,
                        c.card_sha256,
                        c.payload AS card_payload,
                        e.id AS extraction_request_id,
                        e.source_version_id AS request_source_version_id,
                        e.extractor_kind,
                        e.extractor_id,
                        e.extractor_version,
                        e.extraction_model_id,
                        e.extraction_model_revision,
                        e.extraction_prompt_version,
                        e.extraction_prompt_sha256,
                        e.extraction_schema_version,
                        e.extraction_config_sha256,
                        e.request_fingerprint,
                        v.id AS source_version_id,
                        v.source_id,
                        v.version_number AS source_version_number,
                        v.content_sha256 AS source_content_sha256
                    FROM trading_idea_cards AS c
                    JOIN extraction_requests AS e ON e.id = c.extraction_request_id
                    JOIN research_source_versions AS v ON v.id = e.source_version_id
                    WHERE c.id = :card_id
                    """
        if lock_card:
            query += " FOR UPDATE OF c"
        row = (
            connection.execute(
                text(query),
                {"card_id": card_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise MappingNotFoundError(f"card {card_id} was not found")
        payload = row["card_payload"]
        if not isinstance(payload, Mapping):
            raise MappingLineageError("persisted Phase 2 card payload is not an object")
        try:
            card = TradingIdeaCard.model_validate(payload)
        except ValidationError as exc:
            raise MappingLineageError("persisted Phase 2 card payload is invalid") from exc

        cls._assert_equal(card.card_id, row["card_id"], "card_id")
        cls._assert_equal(
            card.extraction_request_id,
            row["card_extraction_request_id"],
            "card.extraction_request_id",
        )
        cls._assert_equal(
            card.extraction_request_id,
            row["extraction_request_id"],
            "extraction_request.id",
        )
        cls._assert_equal(card.source_version_id, row["source_version_id"], "source_version_id")
        cls._assert_equal(
            row["request_source_version_id"], row["source_version_id"], "request.source_version_id"
        )
        cls._assert_equal(card.source_id, row["source_id"], "source_id")
        cls._assert_equal(card.source_version, row["source_version_number"], "source_version")
        cls._assert_equal(
            card.testability_status.value, row["card_testability_status"], "testability"
        )
        cls._assert_equal(
            card.testability_score, row["card_testability_score"], "testability_score"
        )
        cls._assert_equal(card.infra_risk.value, row["card_infra_risk"], "infra_risk")
        cls._assert_equal(
            card.corroboration_status.value,
            row["card_corroboration_status"],
            "corroboration_status",
        )
        cls._assert_equal(
            card.contribution_status.value,
            row["card_contribution_status"],
            "contribution_status",
        )
        calculated_card_hash = canonical_sha256(card.model_dump(mode="json"))
        cls._assert_equal(calculated_card_hash, row["card_sha256"], "card_sha256")

        profile_fields = (
            "extractor_kind",
            "extractor_id",
            "extractor_version",
            "extraction_model_id",
            "extraction_model_revision",
            "extraction_prompt_version",
            "extraction_prompt_sha256",
            "extraction_schema_version",
            "extraction_config_sha256",
        )
        for field in profile_fields:
            card_value = getattr(card, field)
            if hasattr(card_value, "value"):
                card_value = card_value.value
            cls._assert_equal(card_value, row[field], field)

        corroborations = cls._card_corroborations(connection, card_id)
        corroboration_version_ids = tuple(version_id for version_id, _ in corroborations)
        corroboration_source_ids = tuple(
            dict.fromkeys(source_id for _, source_id in corroborations)
        )
        cls._assert_equal(
            tuple(sorted(card.official_corroboration_source_version_ids)),
            corroboration_version_ids,
            "official_corroboration_source_version_ids",
        )
        cls._assert_equal(
            set(card.official_corroboration_source_ids),
            set(corroboration_source_ids),
            "official_corroboration_source_ids",
        )

        try:
            return MappingInput.model_validate(
                {
                    "card_id": card.card_id,
                    "card_sha256": row["card_sha256"],
                    "extraction_request_id": card.extraction_request_id,
                    "extraction_request_fingerprint": row["request_fingerprint"],
                    "source_id": card.source_id,
                    "source_version_id": card.source_version_id,
                    "source_version": card.source_version,
                    "source_content_sha256": row["source_content_sha256"],
                    "official_corroboration_source_version_ids": corroboration_version_ids,
                    "extractor_kind": card.extractor_kind,
                    "extractor_id": card.extractor_id,
                    "extractor_version": card.extractor_version,
                    "extraction_model_id": card.extraction_model_id,
                    "extraction_model_revision": card.extraction_model_revision,
                    "extraction_prompt_version": card.extraction_prompt_version,
                    "extraction_prompt_sha256": card.extraction_prompt_sha256,
                    "extraction_schema_version": card.extraction_schema_version,
                    "extraction_config_sha256": card.extraction_config_sha256,
                    "signal_family": card.signal_family.model_dump(mode="json"),
                    "forecast_horizon": card.forecast_horizon.model_dump(mode="json"),
                    "action_rule": card.action_rule.model_dump(mode="json"),
                    "execution_style": card.execution_style.model_dump(mode="json"),
                    "required_data": card.required_data.model_dump(mode="json"),
                    "testability_status": card.testability_status,
                    "testability_reason_codes": card.testability_reason_codes,
                    "infra_risk": card.infra_risk,
                    "corroboration_status": card.corroboration_status,
                    "contribution_status": card.contribution_status,
                    "source_claim_ids": [claim.claim_id for claim in card.quoted_claims],
                }
            )
        except ValidationError as exc:
            raise MappingLineageError("persisted Phase 2 mapping input is inconsistent") from exc

    @classmethod
    def _existing_for_rule_set(
        cls,
        connection: Connection,
        card_id: UUID,
        rule_set_sha256: str,
    ) -> MappingWithRationale | None:
        row = (
            connection.execute(
                text(
                    "SELECT * FROM research_mapping_versions "
                    "WHERE card_id = :card_id AND mapper_rule_set_sha256 = :rule_set_sha256"
                ),
                {"card_id": card_id, "rule_set_sha256": rule_set_sha256},
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else cls._bundle_from_mapping_row(connection, row)

    @classmethod
    def _validate_mapping_parent_lineage(
        cls,
        mapping: ResearchMapping,
        mapping_input: MappingInput,
    ) -> None:
        expected_fields: tuple[tuple[object, object, str], ...] = (
            (mapping.card_id, mapping_input.card_id, "card_id"),
            (mapping.card_sha256, mapping_input.card_sha256, "card_sha256"),
            (
                mapping.mapping_input_sha256,
                canonical_sha256(mapping_input.model_dump(mode="json")),
                "mapping_input_sha256",
            ),
            (
                mapping.extraction_request_id,
                mapping_input.extraction_request_id,
                "extraction_request_id",
            ),
            (
                mapping.extraction_request_fingerprint,
                mapping_input.extraction_request_fingerprint,
                "extraction_request_fingerprint",
            ),
            (mapping.source_id, mapping_input.source_id, "source_id"),
            (
                mapping.source_version_id,
                mapping_input.source_version_id,
                "source_version_id",
            ),
            (mapping.source_version, mapping_input.source_version, "source_version"),
            (
                mapping.source_content_sha256,
                mapping_input.source_content_sha256,
                "source_content_sha256",
            ),
            (
                mapping.official_corroboration_source_version_ids,
                mapping_input.official_corroboration_source_version_ids,
                "official_corroboration_source_version_ids",
            ),
            (mapping.extractor_kind, mapping_input.extractor_kind, "extractor_kind"),
            (mapping.extractor_id, mapping_input.extractor_id, "extractor_id"),
            (
                mapping.extractor_version,
                mapping_input.extractor_version,
                "extractor_version",
            ),
            (
                mapping.extraction_model_id,
                mapping_input.extraction_model_id,
                "extraction_model_id",
            ),
            (
                mapping.extraction_model_revision,
                mapping_input.extraction_model_revision,
                "extraction_model_revision",
            ),
            (
                mapping.extraction_prompt_version,
                mapping_input.extraction_prompt_version,
                "extraction_prompt_version",
            ),
            (
                mapping.extraction_prompt_sha256,
                mapping_input.extraction_prompt_sha256,
                "extraction_prompt_sha256",
            ),
            (
                mapping.extraction_schema_version,
                mapping_input.extraction_schema_version,
                "extraction_schema_version",
            ),
            (
                mapping.extraction_config_sha256,
                mapping_input.extraction_config_sha256,
                "extraction_config_sha256",
            ),
        )
        for actual, expected, field in expected_fields:
            cls._assert_equal(actual, expected, field)

    @classmethod
    def _validate_existing_mapping(
        cls,
        existing: MappingWithRationale,
        mapping_input: MappingInput,
        decision: MappingDecision,
    ) -> None:
        mapping = existing.mapping
        cls._validate_mapping_parent_lineage(mapping, mapping_input)
        expected_fields: tuple[tuple[object, object, str], ...] = (
            (mapping.mapping_input_sha256, decision.input_sha256, "mapping_input_sha256"),
            (
                mapping.canonical_family,
                decision.canonical_family,
                "canonical_family",
            ),
            (mapping.verdict, decision.verdict, "research_verdict"),
            (mapping.matched_rule_ids, decision.matched_rule_ids, "matched_rule_ids"),
            (mapping.reason_codes, decision.reason_codes, "reason_codes"),
            (
                mapping.mapper_rule_set_version,
                decision.mapper_rule_set_version,
                "mapper_rule_set_version",
            ),
            (
                mapping.mapper_rule_set_sha256,
                decision.mapper_rule_set_sha256,
                "mapper_rule_set_sha256",
            ),
            (mapping.source_evidence, decision.source_evidence, "source_evidence"),
            (
                mapping.rationale_template_version,
                decision.rationale_template_version,
                "rationale_template_version",
            ),
        )
        for actual, expected, field in expected_fields:
            cls._assert_equal(actual, expected, field)

    def create_mapping(
        self,
        card_id: UUID,
        *,
        rule_set: MappingRuleSet = CURRENT_RULE_SET,
    ) -> MappingWithRationale:
        try:
            with self.engine.begin() as connection:
                mapping_input = self._load_mapping_input(connection, card_id)
                decision = map_idea(mapping_input, rule_set)
                existing = self._existing_for_rule_set(connection, card_id, rule_set.sha256)
                if existing is not None:
                    self._validate_existing_mapping(existing, mapping_input, decision)
                    return existing
                version_number = int(
                    connection.execute(
                        text(
                            "SELECT COALESCE(MAX(version_number), 0) + 1 "
                            "FROM research_mapping_versions WHERE card_id = :card_id"
                        ),
                        {"card_id": card_id},
                    ).scalar_one()
                )
                mapping_id = uuid4()
                decision_payload = decision.model_dump(mode="json")
                statement = text(
                    """
                    INSERT INTO research_mapping_versions (
                        id, card_id, version_number, card_sha256, mapping_input_sha256,
                        extraction_request_id, request_fingerprint, source_id,
                        source_version_id, source_version_number, source_content_sha256,
                        extractor_kind, extractor_id, extractor_version,
                        extraction_model_id, extraction_model_revision,
                        extraction_prompt_version, extraction_prompt_sha256,
                        extraction_schema_version, extraction_config_sha256,
                        mapper_rule_set_version, mapper_rule_set_sha256,
                        canonical_family, research_verdict, matched_rule_ids,
                        reason_codes, source_evidence, rationale_template_version
                    ) VALUES (
                        :id, :card_id, :version_number, :card_sha256, :mapping_input_sha256,
                        :extraction_request_id, :request_fingerprint, :source_id,
                        :source_version_id, :source_version_number, :source_content_sha256,
                        :extractor_kind, :extractor_id, :extractor_version,
                        :extraction_model_id, :extraction_model_revision,
                        :extraction_prompt_version, :extraction_prompt_sha256,
                        :extraction_schema_version, :extraction_config_sha256,
                        :mapper_rule_set_version, :mapper_rule_set_sha256,
                        :canonical_family, :research_verdict, :matched_rule_ids,
                        :reason_codes, :source_evidence, :rationale_template_version
                    ) RETURNING *
                    """
                ).bindparams(
                    bindparam("matched_rule_ids", type_=postgresql.JSONB),
                    bindparam("reason_codes", type_=postgresql.JSONB),
                    bindparam("source_evidence", type_=postgresql.JSONB),
                )
                mapping_row = (
                    connection.execute(
                        statement,
                        {
                            "id": mapping_id,
                            "card_id": card_id,
                            "version_number": version_number,
                            "card_sha256": mapping_input.card_sha256,
                            "mapping_input_sha256": decision.input_sha256,
                            "extraction_request_id": mapping_input.extraction_request_id,
                            "request_fingerprint": (mapping_input.extraction_request_fingerprint),
                            "source_id": mapping_input.source_id,
                            "source_version_id": mapping_input.source_version_id,
                            "source_version_number": mapping_input.source_version,
                            "source_content_sha256": mapping_input.source_content_sha256,
                            "extractor_kind": mapping_input.extractor_kind.value,
                            "extractor_id": mapping_input.extractor_id,
                            "extractor_version": mapping_input.extractor_version,
                            "extraction_model_id": mapping_input.extraction_model_id,
                            "extraction_model_revision": (mapping_input.extraction_model_revision),
                            "extraction_prompt_version": (mapping_input.extraction_prompt_version),
                            "extraction_prompt_sha256": (mapping_input.extraction_prompt_sha256),
                            "extraction_schema_version": (mapping_input.extraction_schema_version),
                            "extraction_config_sha256": (mapping_input.extraction_config_sha256),
                            "mapper_rule_set_version": decision.mapper_rule_set_version,
                            "mapper_rule_set_sha256": decision.mapper_rule_set_sha256,
                            "canonical_family": (
                                None
                                if decision.canonical_family is None
                                else decision.canonical_family.value
                            ),
                            "research_verdict": decision.verdict.value,
                            "matched_rule_ids": decision_payload["matched_rule_ids"],
                            "reason_codes": decision_payload["reason_codes"],
                            "source_evidence": decision_payload["source_evidence"],
                            "rationale_template_version": (decision.rationale_template_version),
                        },
                    )
                    .mappings()
                    .one()
                )
                for corroboration_id in mapping_input.official_corroboration_source_version_ids:
                    connection.execute(
                        text(
                            "INSERT INTO mapping_official_corroborations "
                            "(mapping_id, official_source_version_id) "
                            "VALUES (:mapping_id, :official_source_version_id)"
                        ),
                        {
                            "mapping_id": mapping_id,
                            "official_source_version_id": corroboration_id,
                        },
                    )
                mapping = self._mapping_from_row(connection, mapping_row)
                draft_rationale = build_mapping_rationale(mapping)
                rationale_row = (
                    connection.execute(
                        text(
                            """
                            INSERT INTO mapping_rationale_artifacts (
                                id, mapping_id, template_version, markdown_content, content_sha256
                            ) VALUES (
                                :id, :mapping_id, :template_version, :markdown_content,
                                :content_sha256
                            ) RETURNING *
                            """
                        ),
                        {
                            "id": draft_rationale.rationale_id,
                            "mapping_id": mapping.mapping_id,
                            "template_version": draft_rationale.template_version,
                            "markdown_content": draft_rationale.markdown,
                            "content_sha256": draft_rationale.content_sha256,
                        },
                    )
                    .mappings()
                    .one()
                )
                return MappingWithRationale(
                    mapping=mapping,
                    rationale=self._rationale_from_row(rationale_row),
                )
        except MappingNotFoundError:
            raise
        except MappingLineageError:
            raise
        except IntegrityError as exc:
            with self.engine.begin() as connection:
                mapping_input = self._load_mapping_input(connection, card_id)
                decision = map_idea(mapping_input, rule_set)
                existing = self._existing_for_rule_set(connection, card_id, rule_set.sha256)
                if existing is not None:
                    self._validate_existing_mapping(existing, mapping_input, decision)
                    return existing
            raise MappingConflictError("immutable mapping insert conflicted") from exc
        except (DBAPIError, ValidationError, ValueError) as exc:
            raise MappingConflictError("immutable mapping could not be persisted") from exc

    def get_mapping(self, mapping_id: UUID) -> MappingWithRationale:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM research_mapping_versions WHERE id = :mapping_id"),
                    {"mapping_id": mapping_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise MappingNotFoundError(f"mapping {mapping_id} was not found")
            result = self._bundle_from_mapping_row(connection, row)
            mapping_input = self._load_mapping_input(
                connection,
                result.mapping.card_id,
                lock_card=False,
            )
            self._validate_mapping_parent_lineage(result.mapping, mapping_input)
            return result

    def list_mappings(
        self,
        *,
        card_id: UUID | None = None,
        limit: int = 100,
    ) -> list[MappingWithRationale]:
        if limit < 1 or limit > 100:
            raise ValueError("mapping list limit must be between 1 and 100")
        query = "SELECT * FROM research_mapping_versions"
        parameters: dict[str, Any] = {"limit": limit}
        if card_id is not None:
            query += " WHERE card_id = :card_id"
            parameters["card_id"] = card_id
        query += " ORDER BY created_at_utc DESC, id DESC LIMIT :limit"
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), parameters).mappings()
            results: list[MappingWithRationale] = []
            inputs: dict[UUID, MappingInput] = {}
            for row in rows:
                result = self._bundle_from_mapping_row(connection, row)
                mapping_input = inputs.get(result.mapping.card_id)
                if mapping_input is None:
                    mapping_input = self._load_mapping_input(
                        connection,
                        result.mapping.card_id,
                        lock_card=False,
                    )
                    inputs[result.mapping.card_id] = mapping_input
                self._validate_mapping_parent_lineage(result.mapping, mapping_input)
                results.append(result)
            return results


__all__ = [
    "MappingConflictError",
    "MappingLineageError",
    "MappingNotFoundError",
    "MappingRepository",
]
