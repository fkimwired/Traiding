"""Paper-specific credential settings for the explicit Phase 12 operator command."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ALPACA_PAPER_API_KEY_ID_ENV = "FABLE5_ALPACA_PAPER_API_KEY_ID"
ALPACA_PAPER_SECRET_KEY_ENV = "FABLE5_ALPACA_PAPER_SECRET_KEY"


class PaperCredentialsUnavailable(RuntimeError):
    """A sanitized pre-transport credential-gate failure."""

    def __init__(self) -> None:
        super().__init__("paper-readiness credentials are unavailable")


@dataclass(frozen=True, slots=True, repr=False)
class PaperCredentials:
    """Opaque complete credential pair; its representation never renders either secret."""

    api_key_id: SecretStr
    secret_key: SecretStr

    def __repr__(self) -> str:
        return "PaperCredentials(available=True)"


class PaperCredentialSettings(BaseSettings):
    """Load only the two explicitly paper-scoped credential environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FABLE5_ALPACA_PAPER_",
        env_file=None,
        extra="ignore",
        frozen=True,
    )

    api_key_id: SecretStr | None = Field(default=None, validation_alias=ALPACA_PAPER_API_KEY_ID_ENV)
    secret_key: SecretStr | None = Field(default=None, validation_alias=ALPACA_PAPER_SECRET_KEY_ENV)

    def require_credentials(self) -> PaperCredentials:
        values = (self.api_key_id, self.secret_key)
        if any(value is None for value in values):
            raise PaperCredentialsUnavailable
        assert self.api_key_id is not None and self.secret_key is not None
        if not self.api_key_id.get_secret_value().strip() or not (
            self.secret_key.get_secret_value().strip()
        ):
            raise PaperCredentialsUnavailable
        return PaperCredentials(api_key_id=self.api_key_id, secret_key=self.secret_key)


__all__ = [
    "ALPACA_PAPER_API_KEY_ID_ENV",
    "ALPACA_PAPER_SECRET_KEY_ENV",
    "PaperCredentialSettings",
    "PaperCredentials",
    "PaperCredentialsUnavailable",
]
