from __future__ import annotations

from typing import Any

import pytest
from conftest import REQUEST_ID, make_request, make_source
from fable5_extraction.extractor import DeterministicMockExtractor
from fable5_extraction.models import ExtractionEventType
from fable5_extraction.workflow import process_extraction


class MemoryRepository:
    def __init__(self) -> None:
        self.source = make_source(
            "When a stock ranking condition is met, evaluate the next day claim."
        )
        self.request = make_request(self.source).model_copy(
            update={"latest_event": ExtractionEventType.QUEUED}
        )
        self.card: Any = None
        self.memo: Any = None
        self.draft: Any = None
        self.events: list[tuple[ExtractionEventType, dict[str, object]]] = []

    def get_card_for_request(self, request_id: object) -> Any:
        return self.card

    def get_extraction_request(self, request_id: object) -> Any:
        return self.request

    def record_event(
        self, request_id: object, event_type: ExtractionEventType, **kwargs: object
    ) -> Any:
        self.events.append((event_type, kwargs))
        self.request = self.request.model_copy(update={"latest_event": event_type})
        return self.request

    def get_source_version(self, source_version_id: object) -> Any:
        return self.source

    def get_corroborating_versions(self, source_version_id: object) -> list[object]:
        return []

    def complete_extraction(
        self, request_id: object, card: object, memo: object, draft: object
    ) -> Any:
        self.card = card
        self.memo = memo
        self.draft = draft
        self.events.append((ExtractionEventType.SUCCEEDED, {}))
        return card


def test_worker_processing_is_idempotent_and_persists_card_and_memo_atomically() -> None:
    repository = MemoryRepository()
    first = process_extraction(repository, REQUEST_ID)  # type: ignore[arg-type]
    second = process_extraction(repository, REQUEST_ID)  # type: ignore[arg-type]

    assert first == second
    assert repository.card == first
    assert repository.memo.card_id == first.card_id
    assert repository.draft.action_rule.segment_ids
    assert [event for event, _ in repository.events] == [
        ExtractionEventType.STARTED,
        ExtractionEventType.SUCCEEDED,
    ]


class FailingExtractor(DeterministicMockExtractor):
    def extract(self, source: object, segments: object) -> object:
        raise RuntimeError("sensitive failure detail")


def test_worker_failure_records_only_sanitized_error_metadata() -> None:
    repository = MemoryRepository()
    with pytest.raises(RuntimeError, match="sensitive failure detail"):
        process_extraction(  # type: ignore[arg-type]
            repository,
            REQUEST_ID,
            extractor=FailingExtractor(),  # type: ignore[arg-type]
        )

    assert repository.card is None
    event, metadata = repository.events[-1]
    assert event is ExtractionEventType.FAILED
    assert metadata["error_code"] == "phase2_extraction_failed"
    assert metadata["payload"] == {"exception_type": "RuntimeError"}
