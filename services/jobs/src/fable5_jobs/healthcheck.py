from redis import Redis
from sqlalchemy import create_engine, text

from fable5_jobs.config import WorkerSettings


def main() -> None:
    settings = WorkerSettings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as database:
            database.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    connection: Redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        if connection.ping() is not True:
            raise SystemExit(1)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
