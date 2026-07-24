"""Paper-scoped credential gate for the Phase 28 read-only pilot."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fable5_paper.phase12.settings import (
    ALPACA_PAPER_API_KEY_ID_ENV,
    ALPACA_PAPER_SECRET_KEY_ENV,
    PaperCredentials,
    PaperCredentialsUnavailable,
)


class Phase28PaperCredentialSettings(BaseSettings):
    """Load only the accepted paper credential pair."""

    model_config = SettingsConfigDict(
        env_prefix="FABLE5_ALPACA_PAPER_",
        env_file=None,
        extra="ignore",
        frozen=True,
    )

    api_key_id: SecretStr | None = Field(default=None, validation_alias=ALPACA_PAPER_API_KEY_ID_ENV)
    secret_key: SecretStr | None = Field(default=None, validation_alias=ALPACA_PAPER_SECRET_KEY_ENV)

    def require_credentials(self) -> PaperCredentials:
        if self.api_key_id is None or self.secret_key is None:
            raise PaperCredentialsUnavailable
        if (
            not self.api_key_id.get_secret_value().strip()
            or not self.secret_key.get_secret_value().strip()
        ):
            raise PaperCredentialsUnavailable
        return PaperCredentials(api_key_id=self.api_key_id, secret_key=self.secret_key)


__all__ = ["Phase28PaperCredentialSettings"]
