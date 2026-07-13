from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fable5_api.idea_intake import RQExtractionDispatcher
from fable5_extraction.extractor import default_extraction_profile, extraction_fingerprint
from fable5_extraction.models import (
    ContentState,
    ExtractionEventType,
    ExtractionRequestRecord,
    SourceAuthority,
    SourceType,
    SourceVersion,
)
from rq.exceptions import DuplicateJobError


class RecordingQueue:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.kwargs: dict[str, object] = {}

    def enqueue_call(self, function: str, **kwargs: object) -> None:
        if self.duplicate:
            raise DuplicateJobError("duplicate")
        self.kwargs = {"function": function, **kwargs}


def make_request() -> ExtractionRequestRecord:
    now = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)
    raw_text = "When a stock condition occurs, evaluate next day."
    source = SourceVersion(
        source_version_id=UUID("20000000-0000-0000-0000-000000000001"),
        source_id=UUID("10000000-0000-0000-0000-000000000001"),
        source_version=1,
        parent_source_version_id=None,
        source_type=SourceType.SYNTHETIC_FIXTURE,
        source_authority=SourceAuthority.OTHER,
        source_url=None,
        content_state=ContentState.SUPPLIED_TEXT,
        raw_text=raw_text,
        content_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        supplied_at_utc=now,
        retrieved_at_utc=None,
        authority_verification_method=None,
        official_corroboration_source_version_ids=[],
        created_at_utc=now,
    )
    profile = default_extraction_profile()
    fingerprint = extraction_fingerprint(source, profile)
    return ExtractionRequestRecord(
        extraction_request_id=UUID("30000000-0000-0000-0000-000000000001"),
        source_version_id=source.source_version_id,
        **profile.model_dump(),
        request_fingerprint=fingerprint,
        rq_job_id=f"phase2-extract-{fingerprint}",
        latest_event=ExtractionEventType.REQUESTED,
        requested_at_utc=now,
    )


def test_dispatcher_uses_only_research_extraction_job_with_unique_id() -> None:
    dispatcher = RQExtractionDispatcher("redis://localhost:6379/15")
    queue = RecordingQueue()
    dispatcher.queue = queue  # type: ignore[assignment]
    request = make_request()

    assert dispatcher.enqueue(request) is True
    assert queue.kwargs["function"] == "fable5_jobs.extraction.run_extraction"
    assert queue.kwargs["job_id"] == request.rq_job_id
    assert queue.kwargs["unique"] is True
    assert queue.kwargs["args"] == (str(request.extraction_request_id),)


def test_dispatcher_treats_duplicate_job_as_idempotent_noop() -> None:
    dispatcher = RQExtractionDispatcher("redis://localhost:6379/15")
    dispatcher.queue = RecordingQueue(duplicate=True)  # type: ignore[assignment]
    request = make_request()
    assert dispatcher.enqueue(request) is False
