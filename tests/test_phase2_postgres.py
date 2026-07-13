from __future__ import annotations

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fable5_extraction.extractor import default_extraction_profile
from fable5_extraction.models import (
    AuthorityVerificationMethod,
    ContributionStatus,
    SourceAuthority,
    SourceCorrectionRequest,
    SourceIntakeRequest,
    SourceType,
)
from fable5_extraction.repository import IdeaRepository, IdempotencyConflictError
from fable5_extraction.workflow import process_extraction
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set FABLE5_TEST_DATABASE_URL to an isolated PostgreSQL database",
)


def test_postgres_round_trip_versioning_idempotency_and_append_only() -> None:
    assert DATABASE_URL is not None
    prior = os.environ.get("FABLE5_DATABASE_URL")
    os.environ["FABLE5_DATABASE_URL"] = DATABASE_URL
    try:
        config = Config("services/api/alembic.ini")
        command.upgrade(config, "head")
    finally:
        if prior is None:
            os.environ.pop("FABLE5_DATABASE_URL", None)
        else:
            os.environ["FABLE5_DATABASE_URL"] = prior

    repository = IdeaRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        _, official = repository.create_source(
            SourceIntakeRequest(
                source_type=SourceType.SYNTHETIC_FIXTURE,
                source_authority=SourceAuthority.OFFICIAL,
                authority_verification_method=AuthorityVerificationMethod.SYNTHETIC_FIXTURE,
                raw_text="Official synthetic source evidence.",
                ingest_idempotency_key=f"postgres-official-{unique}",
            )
        )
        source, social = repository.create_source(
            SourceIntakeRequest(
                source_type=SourceType.SYNTHETIC_FIXTURE,
                source_authority=SourceAuthority.SOCIAL,
                raw_text="If social attention changes, the source makes a next day stock claim.",
                official_corroboration_source_version_ids=[official.source_version_id],
                ingest_idempotency_key=f"postgres-social-{unique}",
            )
        )
        with pytest.raises(IdempotencyConflictError, match="immutable provenance"):
            repository.create_source(
                SourceIntakeRequest(
                    source_type=SourceType.SYNTHETIC_FIXTURE,
                    source_authority=SourceAuthority.SOCIAL,
                    raw_text=(
                        "If social attention changes, the source makes a next day stock claim."
                    ),
                    official_corroboration_source_version_ids=[],
                    ingest_idempotency_key=f"postgres-social-{unique}",
                )
            )
        request = repository.create_extraction_request(
            social.source_version_id, default_extraction_profile()
        )
        repeated = repository.create_extraction_request(
            social.source_version_id, default_extraction_profile()
        )
        assert repeated.extraction_request_id == request.extraction_request_id
        card = process_extraction(repository, request.extraction_request_id)
        assert card.contribution_status is ContributionStatus.NOT_BLOCKED_BY_CORROBORATION
        assert repository.get_card(card.card_id).memo.card_id == card.card_id

        correction = repository.add_source_version(
            source.source_id,
            SourceCorrectionRequest(
                source_type=SourceType.SYNTHETIC_FIXTURE,
                source_authority=SourceAuthority.SOCIAL,
                raw_text=(
                    "Corrected: if social attention changes, the source makes a weekly stock claim."
                ),
                official_corroboration_source_version_ids=[official.source_version_id],
                ingest_idempotency_key=f"postgres-social-correction-{unique}",
            ),
        )
        assert correction.source_version == 2
        assert correction.parent_source_version_id == social.source_version_id

        update_columns = {
            "research_source_version_corroborations": "source_version_id",
            "card_official_corroborations": "card_id",
        }
        for table in (
            "research_sources",
            "research_source_versions",
            "research_source_version_corroborations",
            "extraction_requests",
            "extraction_events",
            "trading_idea_cards",
            "card_official_corroborations",
            "research_memos",
        ):
            column = update_columns.get(table, "id")
            with repository.engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(f"UPDATE {table} SET {column} = {column}"))
                connection.rollback()
    finally:
        repository.dispose()
