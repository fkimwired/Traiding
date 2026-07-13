import pytest
from fable5_jobs import QUEUE_NAME
from fable5_jobs.config import WorkerSettings
from pydantic import ValidationError


def test_worker_has_one_non_trading_placeholder_queue() -> None:
    assert QUEUE_NAME == "research"
    settings = WorkerSettings(_env_file=None)
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.execution_mode == "paper"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_worker_rejects_any_non_paper_mode() -> None:
    with pytest.raises(ValidationError):
        WorkerSettings(_env_file=None, execution_mode="live")  # type: ignore[arg-type]
