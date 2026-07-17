"""Credential and qualification-use-rights gate for the local Phase 13 capture command."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fable5_data.phase13.contracts import QualificationUseRightsAttestation

TIINGO_RESEARCH_API_TOKEN_ENV = "FABLE5_TIINGO_RESEARCH_API_TOKEN"
TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID_ENV = "FABLE5_TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID"
TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256_ENV = "FABLE5_TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256"
TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC_ENV = "FABLE5_TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC"
TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC_ENV = "FABLE5_TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC"
TIINGO_RESEARCH_STORAGE_ALLOWED_ENV = "FABLE5_TIINGO_RESEARCH_STORAGE_ALLOWED"
TIINGO_RESEARCH_NON_DISPLAY_ALLOWED_ENV = "FABLE5_TIINGO_RESEARCH_NON_DISPLAY_ALLOWED"
TIINGO_RESEARCH_DERIVED_DATA_ALLOWED_ENV = "FABLE5_TIINGO_RESEARCH_DERIVED_DATA_ALLOWED"

PHASE13_TIINGO_ENV_NAMES = (
    TIINGO_RESEARCH_API_TOKEN_ENV,
    TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID_ENV,
    TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256_ENV,
    TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC_ENV,
    TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC_ENV,
    TIINGO_RESEARCH_STORAGE_ALLOWED_ENV,
    TIINGO_RESEARCH_NON_DISPLAY_ALLOWED_ENV,
    TIINGO_RESEARCH_DERIVED_DATA_ALLOWED_ENV,
)


class QualificationAccessUnavailable(RuntimeError):
    """A deliberately generic pre-transport credential/rights failure."""

    def __init__(self) -> None:
        super().__init__("point-in-time qualification access is unavailable")


@dataclass(frozen=True, slots=True, repr=False)
class TiingoQualificationAccess:
    """Opaque complete access pair; repr never renders the provider token."""

    api_token: SecretStr
    rights_attestation: QualificationUseRightsAttestation

    def __repr__(self) -> str:
        return "TiingoQualificationAccess(available=True)"


class TiingoQualificationSettings(BaseSettings):
    """Load only the eight Phase 13 Tiingo research qualification variables."""

    model_config = SettingsConfigDict(
        env_prefix="FABLE5_TIINGO_RESEARCH_",
        env_file=None,
        extra="ignore",
        frozen=True,
    )

    api_token: SecretStr | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_API_TOKEN_ENV,
    )
    rights_attestation_id: str | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID_ENV,
    )
    rights_attestation_sha256: str | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256_ENV,
    )
    rights_valid_from_utc: datetime | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC_ENV,
    )
    rights_expires_at_utc: datetime | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC_ENV,
    )
    storage_allowed: bool | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_STORAGE_ALLOWED_ENV,
    )
    non_display_allowed: bool | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_NON_DISPLAY_ALLOWED_ENV,
    )
    derived_data_allowed: bool | None = Field(
        default=None,
        validation_alias=TIINGO_RESEARCH_DERIVED_DATA_ALLOWED_ENV,
    )

    def require_access(self, *, at_utc: datetime | None = None) -> TiingoQualificationAccess:
        """Return opaque access only when credentials and all rights are complete and current."""

        now = at_utc or datetime.now(UTC)
        if now.tzinfo is None or now.utcoffset() is None:
            raise QualificationAccessUnavailable
        values = (
            self.api_token,
            self.rights_attestation_id,
            self.rights_attestation_sha256,
            self.rights_valid_from_utc,
            self.rights_expires_at_utc,
            self.storage_allowed,
            self.non_display_allowed,
            self.derived_data_allowed,
        )
        if any(value is None for value in values):
            raise QualificationAccessUnavailable
        assert self.api_token is not None
        assert self.rights_attestation_id is not None
        assert self.rights_attestation_sha256 is not None
        assert self.rights_valid_from_utc is not None
        assert self.rights_expires_at_utc is not None
        assert self.storage_allowed is not None
        assert self.non_display_allowed is not None
        assert self.derived_data_allowed is not None
        if not self.api_token.get_secret_value().strip():
            raise QualificationAccessUnavailable
        try:
            rights = QualificationUseRightsAttestation(
                attestation_id=self.rights_attestation_id,
                attestation_sha256=self.rights_attestation_sha256,
                valid_from_utc=self.rights_valid_from_utc,
                expires_at_utc=self.rights_expires_at_utc,
                storage_allowed=self.storage_allowed,
                non_display_allowed=self.non_display_allowed,
                derived_data_allowed=self.derived_data_allowed,
            )
        except Exception as exc:
            raise QualificationAccessUnavailable from exc
        if not rights.is_current_and_sufficient(now):
            raise QualificationAccessUnavailable
        return TiingoQualificationAccess(api_token=self.api_token, rights_attestation=rights)


__all__ = [
    "PHASE13_TIINGO_ENV_NAMES",
    "TIINGO_RESEARCH_API_TOKEN_ENV",
    "TIINGO_RESEARCH_DERIVED_DATA_ALLOWED_ENV",
    "TIINGO_RESEARCH_NON_DISPLAY_ALLOWED_ENV",
    "TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID_ENV",
    "TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256_ENV",
    "TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC_ENV",
    "TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC_ENV",
    "TIINGO_RESEARCH_STORAGE_ALLOWED_ENV",
    "QualificationAccessUnavailable",
    "TiingoQualificationAccess",
    "TiingoQualificationSettings",
]
