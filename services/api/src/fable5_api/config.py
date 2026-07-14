from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FABLE5_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    execution_mode: Literal["paper"] = "paper"
    database_url: str = "postgresql+psycopg://fable5:fable5_dev_only@localhost:5432/fable5"
    redis_url: str = "redis://localhost:6379/0"
    code_version_git_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("code_version_git_sha", mode="before")
    @classmethod
    def empty_git_sha_is_unset(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
