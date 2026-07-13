from __future__ import annotations

from uuid import UUID

from fable5_extraction.repository import IdeaRepository
from fable5_extraction.workflow import process_extraction

from fable5_jobs.config import WorkerSettings


def run_extraction(request_id: str) -> str:
    """Process one immutable extraction request on the research queue."""

    settings = WorkerSettings()
    repository = IdeaRepository(settings.database_url)
    try:
        card = process_extraction(repository, UUID(request_id))
        return str(card.card_id)
    finally:
        repository.dispose()
