from __future__ import annotations

from dataclasses import dataclass

from conftest import FIXED_TIME, make_request, make_source
from fable5_extraction.models import (
    ExtractionEventType,
    SourceCorrectionRequest,
    SourceDetailResponse,
    SourceIntakeRequest,
    SourceRecord,
    SourceType,
)
from fable5_extraction.workflow import IdeaIntakeWorkflow


@dataclass
class RecordingDispatcher:
    calls: list[str]
    fail: bool = False

    def enqueue(self, request: object) -> bool:
        self.calls.append("enqueue")
        if self.fail:
            raise ConnectionError("secret transport detail")
        return True


class RecordingRepository:
    def __init__(self, raw_text: str | None) -> None:
        self.calls: list[str] = []
        self.source = SourceRecord(
            source_id=make_source(raw_text).source_id,
            created_at_utc=FIXED_TIME,
        )
        self.version = make_source(raw_text)
        self.request = make_request(self.version)

    def create_source(self, intake: SourceIntakeRequest) -> tuple[SourceRecord, object]:
        self.calls.append("source_committed")
        return self.source, self.version

    def add_source_version(self, source_id: object, correction: object) -> object:
        self.calls.append("version_committed")
        return self.version

    def get_source(self, source_id: object) -> SourceDetailResponse:
        self.calls.append("source_read")
        return SourceDetailResponse(source=self.source, versions=[self.version])

    def create_extraction_request(self, source_version_id: object, profile: object) -> object:
        assert self.calls == ["source_committed"]
        self.calls.append("request_committed")
        return self.request.model_copy(update={"latest_event": ExtractionEventType.REQUESTED})

    def record_event(
        self,
        request_id: object,
        event_type: ExtractionEventType,
        **kwargs: object,
    ) -> object:
        self.calls.append(event_type.value)
        return self.request.model_copy(update={"latest_event": event_type})

    def get_extraction_request(self, request_id: object) -> object:
        return self.request

    def source_create_response(self, source: object, version: object, extraction: object) -> object:
        from fable5_extraction.models import SourceCreateResponse

        return SourceCreateResponse(source=source, source_version=version, extraction=extraction)


def test_source_commit_precedes_request_commit_and_queue_dispatch() -> None:
    repository = RecordingRepository("When a stock condition occurs, evaluate next day.")
    dispatcher = RecordingDispatcher(repository.calls)
    workflow = IdeaIntakeWorkflow(repository, dispatcher)  # type: ignore[arg-type]

    response = workflow.create_source(
        SourceIntakeRequest(
            source_type=SourceType.MANUAL_NOTES,
            raw_text=repository.version.raw_text,
        )
    )
    assert repository.calls == ["source_committed", "request_committed", "enqueue", "queued"]
    assert response.extraction is not None
    assert response.extraction.latest_event is ExtractionEventType.QUEUED


def test_queue_failure_preserves_source_and_records_sanitized_failure() -> None:
    repository = RecordingRepository("When a stock condition occurs, evaluate next day.")
    dispatcher = RecordingDispatcher(repository.calls, fail=True)
    workflow = IdeaIntakeWorkflow(repository, dispatcher)  # type: ignore[arg-type]

    response = workflow.create_source(
        SourceIntakeRequest(
            source_type=SourceType.MANUAL_NOTES,
            raw_text=repository.version.raw_text,
        )
    )
    assert repository.calls == [
        "source_committed",
        "request_committed",
        "enqueue",
        "enqueue_failed",
    ]
    assert response.source_version == repository.version
    assert response.extraction is not None
    assert response.extraction.latest_event is ExtractionEventType.ENQUEUE_FAILED


def test_url_only_intake_is_persisted_without_extraction_or_network() -> None:
    repository = RecordingRepository(None)
    dispatcher = RecordingDispatcher(repository.calls)
    workflow = IdeaIntakeWorkflow(repository, dispatcher)  # type: ignore[arg-type]

    response = workflow.create_source(
        SourceIntakeRequest(
            source_type=SourceType.URL_PROVENANCE,
            source_url="https://example.invalid/provenance-only",
        )
    )
    assert repository.calls == ["source_committed"]
    assert response.extraction is None


def test_url_only_correction_is_persisted_without_queue_dispatch() -> None:
    repository = RecordingRepository(None)
    dispatcher = RecordingDispatcher(repository.calls)
    workflow = IdeaIntakeWorkflow(repository, dispatcher)  # type: ignore[arg-type]

    response = workflow.add_source_version(
        repository.source.source_id,
        SourceCorrectionRequest(
            source_type=SourceType.URL_PROVENANCE,
            source_url="https://example.invalid/provenance-correction",
        ),
    )

    assert repository.calls == ["version_committed", "source_read"]
    assert response.extraction is None
