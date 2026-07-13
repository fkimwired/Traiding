from fable5_jobs import QUEUE_NAME
from fable5_jobs.config import WorkerSettings


def test_worker_has_one_non_trading_placeholder_queue() -> None:
    assert QUEUE_NAME == "research"
    assert WorkerSettings(_env_file=None).redis_url == "redis://localhost:6379/0"
