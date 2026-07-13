from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FABLE5_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
