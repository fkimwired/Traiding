from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fable5_extraction.extractor import (
    DeterministicMockExtractor,
    Extractor,
    build_card,
    default_extraction_profile,
    segment_source,
)
from fable5_extraction.memo import build_research_memo
from fable5_extraction.models import (
    CardWithMemo,
    ExtractionEventType,
    ExtractionProfile,
    ExtractionRequestRecord,
    ExtractorKind,
    ResearchMemo,
    SourceCorrectionRequest,
    SourceCreateResponse,
    SourceDetailResponse,
    SourceIntakeRequest,
    SourceRecord,
    SourceVersion,
    TradingIdeaCard,
)
from fable5_extraction.repository import IdeaRepository


class ExtractionDispatcher(Protocol):
    def enqueue(self, request: ExtractionRequestRecord) -> bool: ...


class IdeaIntakeWorkflow:
    def __init__(self, repository: IdeaRepository, dispatcher: ExtractionDispatcher) -> None:
        self.repository = repository
        self.dispatcher = dispatcher

    def _enqueue(self, source_version_id: UUID) -> ExtractionRequestRecord:
        request = self.repository.create_extraction_request(
            source_version_id, default_extraction_profile()
        )
        if request.latest_event in {
            ExtractionEventType.QUEUED,
            ExtractionEventType.STARTED,
            ExtractionEventType.SUCCEEDED,
        }:
            return request
        try:
            enqueued = self.dispatcher.enqueue(request)
        except Exception as exc:
            return self.repository.record_event(
                request.extraction_request_id,
                ExtractionEventType.ENQUEUE_FAILED,
                error_code="research_queue_unavailable",
                payload={"exception_type": type(exc).__name__},
            )
        if not enqueued:
            return self.repository.get_extraction_request(request.extraction_request_id)
        return self.repository.record_event(
            request.extraction_request_id,
            ExtractionEventType.QUEUED,
        )

    def create_source(self, intake: SourceIntakeRequest) -> SourceCreateResponse:
        source, version = self.repository.create_source(intake)
        extraction = (
            self._enqueue(version.source_version_id) if intake.raw_text is not None else None
        )
        return self.repository.source_create_response(source, version, extraction)

    def add_source_version(
        self, source_id: UUID, correction: SourceCorrectionRequest
    ) -> SourceCreateResponse:
        version = self.repository.add_source_version(source_id, correction)
        source = self.repository.get_source(source_id).source
        extraction = (
            self._enqueue(version.source_version_id) if correction.raw_text is not None else None
        )
        return self.repository.source_create_response(source, version, extraction)

    def request_extraction(self, source_version_id: UUID) -> ExtractionRequestRecord:
        return self._enqueue(source_version_id)

    def list_sources(self, limit: int) -> list[SourceRecord]:
        return self.repository.list_sources(limit)

    def get_source(self, source_id: UUID) -> SourceDetailResponse:
        return self.repository.get_source(source_id)

    def get_source_version(self, source_version_id: UUID) -> SourceVersion:
        return self.repository.get_source_version(source_version_id)

    def list_extractions(self, limit: int) -> list[ExtractionRequestRecord]:
        return self.repository.list_extraction_requests(limit)

    def get_extraction(self, request_id: UUID) -> ExtractionRequestRecord:
        return self.repository.get_extraction_request(request_id)

    def list_cards(self, limit: int) -> list[TradingIdeaCard]:
        return self.repository.list_cards(limit)

    def get_card(self, card_id: UUID) -> CardWithMemo:
        return self.repository.get_card(card_id)

    def get_memo(self, card_id: UUID) -> ResearchMemo:
        return self.repository.get_memo(card_id)


def process_extraction(
    repository: IdeaRepository,
    request_id: UUID,
    *,
    extractor: Extractor | None = None,
) -> TradingIdeaCard:
    existing = repository.get_card_for_request(request_id)
    if existing is not None:
        return existing

    request = repository.get_extraction_request(request_id)
    if request.extractor_kind is not ExtractorKind.DETERMINISTIC_MOCK:
        repository.record_event(
            request_id,
            ExtractionEventType.FAILED,
            error_code="unsupported_extractor_kind",
        )
        raise ValueError("only the deterministic Phase 2 extractor is configured")

    repository.record_event(request_id, ExtractionEventType.STARTED)
    try:
        source = repository.get_source_version(request.source_version_id)
        corroborating_versions = repository.get_corroborating_versions(source.source_version_id)
        active_extractor = extractor or DeterministicMockExtractor()
        if active_extractor.profile != ExtractionProfile(
            **request.model_dump(
                include={
                    "extractor_kind",
                    "extractor_id",
                    "extractor_version",
                    "extraction_model_id",
                    "extraction_model_revision",
                    "extraction_prompt_version",
                    "extraction_prompt_sha256",
                    "extraction_schema_version",
                    "extraction_config_sha256",
                }
            )
        ):
            raise ValueError("extractor profile does not match the immutable request")
        segments = segment_source(source.raw_text)
        draft = active_extractor.extract(source, segments)
        card = build_card(
            source=source,
            request=request,
            draft=draft,
            segments=segments,
            corroborating_versions=corroborating_versions,
        )
        memo = build_research_memo(card)
        return repository.complete_extraction(request_id, card, memo, draft)
    except Exception as exc:
        repository.record_event(
            request_id,
            ExtractionEventType.FAILED,
            error_code="phase2_extraction_failed",
            payload={"exception_type": type(exc).__name__},
        )
        raise
