"""Vendor-neutral Phase 4 adapter boundaries.

This module deliberately contains no provider SDK import and no network implementation.  The
credential gate is evaluated before a transport factory is constructed so missing credentials
cannot cause DNS, socket, HTTP, or SDK initialization side effects.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from fable5_data.contracts import (
    AdapterProfile,
    AdapterResult,
    AdapterUnavailableReason,
    AdapterUnavailableResult,
    DataCapability,
)


@runtime_checkable
class Phase4DataAdapter(Protocol):
    """The only surface snapshot orchestration needs from a data adapter."""

    @property
    def profile(self) -> AdapterProfile: ...

    def fetch(self, capability: DataCapability) -> AdapterResult:
        """Return typed observations or a sanitized unavailable result."""


@runtime_checkable
class AdapterTransport(Protocol):
    """A late-created transport boundary, intentionally free of vendor SDK types."""

    def fetch(self, capability: DataCapability) -> AdapterResult:
        """Fetch a declared capability."""


TransportFactory = Callable[[], AdapterTransport]


class CredentialGatedAdapter:
    """Fail closed before transport construction when credentials are unavailable.

    The class accepts only a boolean availability decision.  It never accepts or stores a
    credential value, which prevents secrets from leaking through ``repr``, exceptions, model
    dumps, logs, fixtures, or snapshot inputs.
    """

    __slots__ = ("_credentials_available", "_profile", "_transport_factory")

    def __init__(
        self,
        *,
        profile: AdapterProfile,
        credentials_available: bool,
        transport_factory: TransportFactory,
    ) -> None:
        self._profile = profile
        self._credentials_available = credentials_available
        self._transport_factory = transport_factory

    @property
    def profile(self) -> AdapterProfile:
        return self._profile

    def __repr__(self) -> str:
        state = "available" if self._credentials_available else "unavailable"
        return (
            "CredentialGatedAdapter("
            f"adapter_id={self.profile.adapter_id!r}, credential_state={state!r})"
        )

    def fetch(self, capability: DataCapability) -> AdapterResult:
        if not self._credentials_available:
            return self._unavailable(
                capability,
                AdapterUnavailableReason.CREDENTIALS_UNAVAILABLE,
                "credentials unavailable before transport initialization",
            )
        if capability not in self.profile.capabilities:
            return self._unavailable(
                capability,
                AdapterUnavailableReason.CAPABILITY_UNAVAILABLE,
                "requested capability unavailable for adapter",
            )

        # This is intentionally the first point at which a transport object may be constructed.
        transport = self._transport_factory()
        try:
            return transport.fetch(capability)
        except Exception:
            return self._unavailable(
                capability,
                AdapterUnavailableReason.CONFIGURATION_UNAVAILABLE,
                "adapter transport unavailable",
            )

    def _unavailable(
        self,
        capability: DataCapability,
        reason: AdapterUnavailableReason,
        message: str,
    ) -> AdapterUnavailableResult:
        rights = self.profile.use_rights
        return AdapterUnavailableResult(
            reason_code=reason,
            capability=capability,
            provider_id=self.profile.provider_id,
            adapter_id=self.profile.adapter_id,
            adapter_version=self.profile.adapter_version,
            dataset_id=self.profile.dataset_id,
            product_id=self.profile.product_id,
            entitlement_id=rights.entitlement_id,
            use_rights_id=rights.use_rights_id,
            sanitized_message=message,
        )


__all__ = [
    "AdapterTransport",
    "CredentialGatedAdapter",
    "Phase4DataAdapter",
    "TransportFactory",
]
