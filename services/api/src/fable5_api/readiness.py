from redis import Redis
from sqlalchemy import create_engine, text

from fable5_api.config import Settings
from fable5_api.schemas import DependencyStatus


def check_dependencies(settings: Settings) -> DependencyStatus:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()

    redis_client: Redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        redis_client.ping()
    finally:
        redis_client.close()

    return DependencyStatus()
