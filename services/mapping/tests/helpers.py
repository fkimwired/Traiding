"""Synthetic Phase 2 builders used only by Phase 3 mapping tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

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
from fable5_mapping.models import MappingInput
from fable5_mapping.rules import canonical_sha256

FIXED_TIME = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)
SOURCE_ID = UUID("11000000-0000-0000-0000-000000000001")
SOURCE_VERSION_ID = UUID("22000000-0000-0000-0000-000000000001")
REQUEST_ID = UUID("33000000-0000-0000-0000-000000000001")
CARD_ID = UUID("44000000-0000-0000-0000-000000000001")


def make_source(
    raw_text: str,
    *,
    authority: SourceAuthority = SourceAuthority.OTHER,
    source_version_id: UUID = SOURCE_VERSION_ID,
) -> SourceVersion:
    return SourceVersion(
        source_version_id=source_version_id,
        source_id=SOURCE_ID,
        source_version=1,
        parent_source_version_id=None,
        source_type=SourceType.SYNTHETIC_FIXTURE,
        source_authority=authority,
        source_url=None,
        content_state=ContentState.SUPPLIED_TEXT,
        raw_text=raw_text,
        content_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        supplied_at_utc=FIXED_TIME,
        retrieved_at_utc=None,
        authority_verification_method=None,
        official_corroboration_source_version_ids=[],
        created_at_utc=FIXED_TIME,
    )


def make_request(source: SourceVersion) -> ExtractionRequestRecord:
    profile = default_extraction_profile()
    fingerprint = extraction_fingerprint(source, profile)
    return ExtractionRequestRecord(
        extraction_request_id=REQUEST_ID,
        source_version_id=source.source_version_id,
        **profile.model_dump(),
        request_fingerprint=fingerprint,
        rq_job_id=f"phase2-extract-{fingerprint}",
        latest_event=ExtractionEventType.SUCCEEDED,
        requested_at_utc=FIXED_TIME,
    )


def make_card(
    raw_text: str,
    *,
    authority: SourceAuthority = SourceAuthority.OTHER,
    corroborating_versions: list[SourceVersion] | None = None,
) -> tuple[TradingIdeaCard, SourceVersion, ExtractionRequestRecord]:
    source = make_source(raw_text, authority=authority)
    request = make_request(source)
    segments = segment_source(raw_text)
    draft = DeterministicMockExtractor().extract(source, segments)
    card = build_card(
        source=source,
        request=request,
        draft=draft,
        segments=segments,
        corroborating_versions=corroborating_versions or [],
        card_id=CARD_ID,
        created_at_utc=FIXED_TIME,
    )
    return card, source, request


def mapping_input(
    card: TradingIdeaCard,
    source: SourceVersion,
    request: ExtractionRequestRecord,
) -> MappingInput:
    return MappingInput.model_validate(
        {
            "card_id": card.card_id,
            "card_sha256": canonical_sha256(card.model_dump(mode="json")),
            "extraction_request_id": card.extraction_request_id,
            "extraction_request_fingerprint": request.request_fingerprint,
            "source_id": card.source_id,
            "source_version_id": card.source_version_id,
            "source_version": card.source_version,
            "source_content_sha256": source.content_sha256,
            "official_corroboration_source_version_ids": (
                card.official_corroboration_source_version_ids
            ),
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


def make_mapping_input(
    raw_text: str,
    *,
    authority: SourceAuthority = SourceAuthority.OTHER,
    corroborating_versions: list[SourceVersion] | None = None,
) -> MappingInput:
    card, source, request = make_card(
        raw_text,
        authority=authority,
        corroborating_versions=corroborating_versions,
    )
    return mapping_input(card, source, request)
