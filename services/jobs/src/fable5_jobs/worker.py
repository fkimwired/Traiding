from redis import Redis
from rq import Worker

from fable5_jobs import QUEUE_NAME
from fable5_jobs.config import WorkerSettings


def run() -> None:
    settings = WorkerSettings()
    connection: Redis = Redis.from_url(settings.redis_url)
    worker = Worker([QUEUE_NAME], connection=connection, name="fable5-phase1-worker")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    run()
