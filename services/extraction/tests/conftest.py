from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fable5_extraction.extractor import (
    DeterministicMockExtractor,
    build_card,
    default_extraction_profile,
    extraction_fingerprint,
    segment_source,
)
from fable5_extraction.models import (
    ContentState,
    ExtractionEventType,
    ExtractionRequestRecord,
    SourceAuthority,
    SourceType,
    SourceVersion,
    TradingIdeaCard,
)

FIXED_TIME = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)
SOURCE_ID = UUID("10000000-0000-0000-0000-000000000001")
SOURCE_VERSION_ID = UUID("20000000-0000-0000-0000-000000000001")
REQUEST_ID = UUID("30000000-0000-0000-0000-000000000001")
CARD_ID = UUID("40000000-0000-0000-0000-000000000001")


def make_source(
    raw_text: str | None,
    *,
    authority: SourceAuthority = SourceAuthority.OTHER,
    source_type: SourceType = SourceType.SYNTHETIC_FIXTURE,
    source_version_id: UUID = SOURCE_VERSION_ID,
) -> SourceVersion:
    content = b"" if raw_text is None else raw_text.encode("utf-8")
    return SourceVersion(
        source_version_id=source_version_id,
        source_id=SOURCE_ID,
        source_version=1,
        parent_source_version_id=None,
        source_type=source_type,
        source_authority=authority,
        source_url="https://example.invalid/synthetic" if raw_text is None else None,
        content_state=(
            ContentState.URL_ONLY_UNRETRIEVED if raw_text is None else ContentState.SUPPLIED_TEXT
        ),
        raw_text=raw_text,
        content_sha256=hashlib.sha256(content).hexdigest(),
        supplied_at_utc=FIXED_TIME,
        retrieved_at_utc=None,
        authority_verification_method=None,
        official_corroboration_source_version_ids=[],
        created_at_utc=FIXED_TIME,
    )


def make_request(source: SourceVersion) -> ExtractionRequestRecord:
    profile = default_extraction_profile()
    return ExtractionRequestRecord(
        extraction_request_id=REQUEST_ID,
        source_version_id=source.source_version_id,
        **profile.model_dump(),
        request_fingerprint=extraction_fingerprint(source, profile),
        rq_job_id=f"phase2-extract-{extraction_fingerprint(source, profile)}",
        latest_event=ExtractionEventType.STARTED,
        requested_at_utc=FIXED_TIME,
    )


@pytest.fixture
def build_fixture_card() -> object:
    def build(
        raw_text: str,
        *,
        authority: SourceAuthority = SourceAuthority.OTHER,
        corroborating_versions: list[SourceVersion] | None = None,
    ) -> TradingIdeaCard:
        source = make_source(raw_text, authority=authority)
        request = make_request(source)
        segments = segment_source(raw_text)
        draft = DeterministicMockExtractor().extract(source, segments)
        return build_card(
            source=source,
            request=request,
            draft=draft,
            segments=segments,
            corroborating_versions=corroborating_versions or [],
            card_id=CARD_ID,
            created_at_utc=FIXED_TIME,
        )

    return build
