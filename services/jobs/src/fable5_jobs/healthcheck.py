from redis import Redis

from fable5_jobs.config import WorkerSettings


def main() -> None:
    settings = WorkerSettings()
    connection: Redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        if connection.ping() is not True:
            raise SystemExit(1)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
