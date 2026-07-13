from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, get_ident
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fable5_extraction.extractor import default_extraction_profile
from fable5_extraction.models import (
    AuthorityVerificationMethod,
    SourceAuthority,
    SourceIntakeRequest,
    SourceType,
    TradingIdeaCard,
)
from fable5_extraction.repository import IdeaRepository
from fable5_extraction.workflow import process_extraction
from fable5_mapping.models import CanonicalFamily, MappingWithRationale, ResearchVerdict
from fable5_mapping.repository import MappingRepository
from fable5_mapping.rules import CURRENT_RULE_SET, MappingRuleSet
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set FABLE5_TEST_DATABASE_URL to an isolated PostgreSQL database",
)


def _upgrade_head(database_url: str) -> None:
    prior = os.environ.get("FABLE5_DATABASE_URL")
    os.environ["FABLE5_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config("services/api/alembic.ini"), "head")
    finally:
        if prior is None:
            os.environ.pop("FABLE5_DATABASE_URL", None)
        else:
            os.environ["FABLE5_DATABASE_URL"] = prior


def _create_testable_trend_card(
    repository: IdeaRepository,
    *,
    key: str,
    suffix: str = "",
) -> TradingIdeaCard:
    _, source = repository.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.OTHER,
            raw_text=(
                "When the moving average crosses, evaluate the next day trend claim. " + suffix
            ).strip(),
            ingest_idempotency_key=key,
        )
    )
    request = repository.create_extraction_request(
        source.source_version_id,
        default_extraction_profile(),
    )
    return process_extraction(repository, request.extraction_request_id)


def _create_corroborated_social_card(
    repository: IdeaRepository,
    *,
    key: str,
) -> tuple[TradingIdeaCard, UUID]:
    _, official = repository.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.OFFICIAL,
            authority_verification_method=AuthorityVerificationMethod.SYNTHETIC_FIXTURE,
            raw_text="Official event corroboration.",
            ingest_idempotency_key=f"{key}-official",
        )
    )
    _, extra_official = repository.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.OFFICIAL,
            authority_verification_method=AuthorityVerificationMethod.SYNTHETIC_FIXTURE,
            raw_text="Independent official event corroboration.",
            ingest_idempotency_key=f"{key}-extra-official",
        )
    )
    _, social = repository.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.SOCIAL,
            raw_text=(
                "If social attention changes around an issuer event, evaluate the next day "
                "stock claim."
            ),
            official_corroboration_source_version_ids=[official.source_version_id],
            ingest_idempotency_key=f"{key}-social",
        )
    )
    request = repository.create_extraction_request(
        social.source_version_id,
        default_extraction_profile(),
    )
    card = process_extraction(repository, request.extraction_request_id)
    return card, extra_official.source_version_id


def _create_concurrently(
    card_id: UUID,
    rule_sets: tuple[MappingRuleSet, MappingRuleSet],
) -> list[tuple[int, MappingWithRationale]]:
    assert DATABASE_URL is not None
    repositories = (MappingRepository(DATABASE_URL), MappingRepository(DATABASE_URL))
    barrier = Barrier(2)

    def worker(index: int) -> tuple[int, MappingWithRationale]:
        barrier.wait(timeout=15)
        return (
            get_ident(),
            repositories[index].create_mapping(card_id, rule_set=rule_sets[index]),
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            return [future.result(timeout=30) for future in futures]
    finally:
        for repository in repositories:
            repository.dispose()


MAPPING_COLUMNS = (
    "id",
    "card_id",
    "version_number",
    "card_sha256",
    "mapping_input_sha256",
    "extraction_request_id",
    "request_fingerprint",
    "source_id",
    "source_version_id",
    "source_version_number",
    "source_content_sha256",
    "extractor_kind",
    "extractor_id",
    "extractor_version",
    "extraction_model_id",
    "extraction_model_revision",
    "extraction_prompt_version",
    "extraction_prompt_sha256",
    "extraction_schema_version",
    "extraction_config_sha256",
    "mapper_rule_set_version",
    "mapper_rule_set_sha256",
    "canonical_family",
    "research_verdict",
    "matched_rule_ids",
    "reason_codes",
    "source_evidence",
    "rationale_template_version",
)


def _clone_mapping_insert(field: str | None) -> str:
    replacements = {
        "id": ":new_id",
        "version_number": ":version_number",
        "mapper_rule_set_version": ":rule_set_version",
        "mapper_rule_set_sha256": ":rule_set_sha256",
    }
    if field is not None:
        replacements[field] = ":mismatch"
    selected = [replacements.get(column, f"original.{column}") for column in MAPPING_COLUMNS]
    return (
        f"INSERT INTO research_mapping_versions ({', '.join(MAPPING_COLUMNS)}) "
        f"SELECT {', '.join(selected)} FROM research_mapping_versions AS original "
        "WHERE original.id = :original_id"
    )


def test_phase3_postgres_idempotency_versioning_lineage_and_append_only() -> None:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    idea_repository = IdeaRepository(DATABASE_URL)
    mapping_repository = MappingRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        _, source = idea_repository.create_source(
            SourceIntakeRequest(
                source_type=SourceType.SYNTHETIC_FIXTURE,
                source_authority=SourceAuthority.OTHER,
                raw_text="When the moving average crosses, evaluate the next day trend claim.",
                ingest_idempotency_key=f"phase3-postgres-trend-{unique}",
            )
        )
        request = idea_repository.create_extraction_request(
            source.source_version_id,
            default_extraction_profile(),
        )
        card = process_extraction(idea_repository, request.extraction_request_id)

        first = mapping_repository.create_mapping(card.card_id)
        repeated = mapping_repository.create_mapping(card.card_id)

        assert repeated == first
        assert first.mapping.mapping_version == 1
        assert first.mapping.canonical_family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
        assert first.mapping.verdict is ResearchVerdict.BUILD_RESEARCH
        assert first.mapping.card_id == card.card_id
        assert first.mapping.extraction_request_id == request.extraction_request_id
        assert first.mapping.source_id == source.source_id
        assert first.mapping.source_version_id == source.source_version_id
        assert first.mapping.extraction_schema_version == card.extraction_schema_version
        assert first.mapping.extraction_config_sha256 == card.extraction_config_sha256
        assert first.rationale.mapping_id == first.mapping.mapping_id

        changed_rules = replace(
            CURRENT_RULE_SET,
            version="phase3-canon-mapping-v2-postgres-test",
        )
        revised = mapping_repository.create_mapping(card.card_id, rule_set=changed_rules)
        assert revised.mapping.mapping_id != first.mapping.mapping_id
        assert revised.mapping.mapping_version == 2
        assert revised.mapping.mapper_rule_set_sha256 == changed_rules.sha256
        assert mapping_repository.get_mapping(first.mapping.mapping_id) == first
        assert [
            item.mapping.mapping_version
            for item in mapping_repository.list_mappings(card_id=card.card_id, limit=10)
        ] == [2, 1]

        for table in (
            "research_mapping_versions",
            "mapping_official_corroborations",
            "mapping_rationale_artifacts",
        ):
            statement = (
                f"TRUNCATE {table}"
                if table == "mapping_official_corroborations"
                else f"UPDATE {table} SET id = id"
            )
            with mapping_repository.engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(statement))
                connection.rollback()
    finally:
        mapping_repository.dispose()
        idea_repository.dispose()


def test_phase3_postgres_rejects_every_mismatched_phase2_lineage_field() -> None:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    idea_repository = IdeaRepository(DATABASE_URL)
    mapping_repository = MappingRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        original_card = _create_testable_trend_card(
            idea_repository,
            key=f"phase3-lineage-original-{unique}",
        )
        alternate_card = _create_testable_trend_card(
            idea_repository,
            key=f"phase3-lineage-alternate-{unique}",
            suffix="Alternate source evidence.",
        )
        original = mapping_repository.create_mapping(original_card.card_id)
        alternate = mapping_repository.create_mapping(alternate_card.card_id)

        mismatches: dict[str, object] = {
            "extraction_request_id": alternate.mapping.extraction_request_id,
            "card_sha256": "0" * 64,
            "request_fingerprint": alternate.mapping.extraction_request_fingerprint,
            "source_version_id": alternate.mapping.source_version_id,
            "source_id": alternate.mapping.source_id,
            "source_version_number": original.mapping.source_version + 1,
            "source_content_sha256": alternate.mapping.source_content_sha256,
            "extractor_kind": "llm",
            "extractor_id": "mismatched-extractor",
            "extractor_version": "mismatched-version",
            "extraction_model_id": "mismatched-model",
            "extraction_model_revision": "mismatched-revision",
            "extraction_prompt_version": "mismatched-prompt",
            "extraction_prompt_sha256": "0" * 64,
            "extraction_schema_version": "mismatched-schema",
            "extraction_config_sha256": "0" * 64,
        }
        for offset, (field, mismatch) in enumerate(mismatches.items(), start=10):
            with mapping_repository.engine.connect() as connection:
                with pytest.raises(
                    DBAPIError,
                    match=f"Phase 3 mapping lineage mismatch: {field}",
                ):
                    connection.execute(
                        text(_clone_mapping_insert(field)),
                        {
                            "new_id": uuid4(),
                            "version_number": offset,
                            "rule_set_version": f"negative-lineage-{field}",
                            "rule_set_sha256": f"{offset:064x}",
                            "mismatch": mismatch,
                            "original_id": original.mapping.mapping_id,
                        },
                    )
                connection.rollback()
    finally:
        mapping_repository.dispose()
        idea_repository.dispose()


def test_phase3_postgres_rejects_missing_and_extra_corroboration_sets_at_commit() -> None:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    idea_repository = IdeaRepository(DATABASE_URL)
    mapping_repository = MappingRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        card, extra_official_id = _create_corroborated_social_card(
            idea_repository,
            key=f"phase3-corroboration-set-{unique}",
        )
        original = mapping_repository.create_mapping(card.card_id)
        assert original.mapping.official_corroboration_source_version_ids

        with mapping_repository.engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text(_clone_mapping_insert(None)),
                {
                    "new_id": uuid4(),
                    "version_number": 2,
                    "rule_set_version": "missing-corroboration-negative-test",
                    "rule_set_sha256": "1" * 64,
                    "original_id": original.mapping.mapping_id,
                },
            )
            with pytest.raises(DBAPIError, match="mapping corroboration set mismatch"):
                transaction.commit()

        with mapping_repository.engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError, match="corroboration lineage is finalized"):
                connection.execute(
                    text(
                        "INSERT INTO mapping_official_corroborations "
                        "(mapping_id, official_source_version_id) "
                        "VALUES (:mapping_id, :official_source_version_id)"
                    ),
                    {
                        "mapping_id": original.mapping.mapping_id,
                        "official_source_version_id": extra_official_id,
                    },
                )
            transaction.rollback()

        with mapping_repository.engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError, match="corroboration lineage is finalized"):
                connection.execute(
                    text(
                        "INSERT INTO card_official_corroborations "
                        "(card_id, official_source_version_id) "
                        "VALUES (:card_id, :official_source_version_id)"
                    ),
                    {
                        "card_id": card.card_id,
                        "official_source_version_id": extra_official_id,
                    },
                )
                connection.execute(
                    text(
                        "INSERT INTO mapping_official_corroborations "
                        "(mapping_id, official_source_version_id) "
                        "VALUES (:mapping_id, :official_source_version_id)"
                    ),
                    {
                        "mapping_id": original.mapping.mapping_id,
                        "official_source_version_id": extra_official_id,
                    },
                )
            transaction.rollback()
    finally:
        mapping_repository.dispose()
        idea_repository.dispose()


def test_phase3_postgres_concurrent_identical_hash_is_one_idempotent_row() -> None:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    idea_repository = IdeaRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        card = _create_testable_trend_card(
            idea_repository,
            key=f"phase3-concurrency-identical-{unique}",
        )
        results = _create_concurrently(
            card.card_id,
            (CURRENT_RULE_SET, CURRENT_RULE_SET),
        )

        assert len({thread_id for thread_id, _ in results}) == 2
        assert len({result.mapping.mapping_id for _, result in results}) == 1
        with idea_repository.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT version_number, mapper_rule_set_sha256 "
                    "FROM research_mapping_versions WHERE card_id = :card_id "
                    "ORDER BY version_number"
                ),
                {"card_id": card.card_id},
            ).all()
        assert [(row.version_number, row.mapper_rule_set_sha256) for row in rows] == [
            (1, CURRENT_RULE_SET.sha256)
        ]
    finally:
        idea_repository.dispose()


def test_phase3_postgres_concurrent_changed_hashes_are_gap_free_versions() -> None:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    idea_repository = IdeaRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        card = _create_testable_trend_card(
            idea_repository,
            key=f"phase3-concurrency-changed-{unique}",
        )
        rule_sets = (
            replace(CURRENT_RULE_SET, version="phase3-concurrent-alpha"),
            replace(CURRENT_RULE_SET, version="phase3-concurrent-beta"),
        )
        results = _create_concurrently(card.card_id, rule_sets)

        assert len({thread_id for thread_id, _ in results}) == 2
        assert len({result.mapping.mapping_id for _, result in results}) == 2
        with idea_repository.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT version_number, mapper_rule_set_sha256 "
                    "FROM research_mapping_versions WHERE card_id = :card_id "
                    "ORDER BY version_number"
                ),
                {"card_id": card.card_id},
            ).all()
        assert [row.version_number for row in rows] == [1, 2]
        assert {row.mapper_rule_set_sha256 for row in rows} == {
            rule_set.sha256 for rule_set in rule_sets
        }
    finally:
        idea_repository.dispose()
