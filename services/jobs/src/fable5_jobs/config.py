from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FABLE5_", extra="ignore")

    execution_mode: Literal["paper"] = "paper"
    database_url: str = "postgresql+psycopg://fable5:fable5_dev_only@localhost:5432/fable5"
    redis_url: str = "redis://localhost:6379/0"
