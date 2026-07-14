from __future__ import annotations

import inspect
from importlib.resources import files

import pytest
from fable5_data.adapters import CredentialGatedAdapter, Phase4DataAdapter
from fable5_data.contracts import (
    CAPABILITY_RECORD_TYPES,
    SYNTHETIC_ADAPTER_VERSION,
    SYNTHETIC_FIXTURE_SET_VERSION,
    AdapterProfile,
    AdapterUnavailableReason,
    DataCapability,
    DataRecordType,
    UseRightsScope,
)
from fable5_data.synthetic import (
    SYNTHETIC_ADAPTER_PROFILE,
    SyntheticPointInTimeAdapter,
    fixture_set_sha256,
)


def test_synthetic_adapter_declares_and_serves_all_nine_capabilities() -> None:
    adapter = SyntheticPointInTimeAdapter()

    assert isinstance(adapter, Phase4DataAdapter)
    assert len(adapter.profile.capabilities) == 9
    assert set(adapter.profile.capabilities) == set(DataCapability)
    assert adapter.profile.adapter_version == SYNTHETIC_ADAPTER_VERSION
    assert adapter.profile.synthetic is True
    assert len(adapter.profile.schema_bindings) == len(DataRecordType)

    observed_types: set[DataRecordType] = set()
    for capability in DataCapability:
        result = adapter.fetch(capability)
        assert result.status == "available"
        assert result.capability is capability
        record_types = {
            DataRecordType(item.payload.record_type)
            for item in result.batch.normalized_observations
        }
        assert record_types == CAPABILITY_RECORD_TYPES[capability]
        observed_types.update(record_types)
    assert observed_types == set(DataRecordType)


def test_synthetic_outputs_are_byte_stable_and_use_frozen_retrieval_times() -> None:
    first = SyntheticPointInTimeAdapter()
    second = SyntheticPointInTimeAdapter()

    assert first.all_results() == second.all_results()
    assert (
        fixture_set_sha256() == "d86c0ad18228c05ef199abba7b4e25e761c4d4f190b0bf30617c435a550172f9"
    )
    retrieved = {
        item.retrieved_at
        for result in first.all_results()
        for item in result.batch.normalized_observations
    }
    assert len(retrieved) == 1
    assert next(iter(retrieved)).isoformat() == "2024-01-02T12:00:00+00:00"
    assert all(
        item.adapter_version == SYNTHETIC_ADAPTER_VERSION
        for result in first.all_results()
        for item in result.batch.normalized_observations
    )


def test_fixture_is_clearly_versioned_and_adapter_has_no_network_or_sdk_imports() -> None:
    import fable5_data.adapters as adapter_module
    import fable5_data.synthetic as synthetic_module

    sources = (inspect.getsource(adapter_module) + inspect.getsource(synthetic_module)).casefold()
    forbidden_imports = (
        "import requests",
        "import httpx",
        "import aiohttp",
        "import boto",
        "import polygon",
        "import alpaca",
        "import yfinance",
        "import socket",
    )

    fixture_text = (
        files("fable5_data")
        .joinpath("fixtures/phase4_synthetic_pit_v1.json")
        .read_text(encoding="utf-8")
    )
    assert SYNTHETIC_FIXTURE_SET_VERSION in fixture_text
    assert all(forbidden not in sources for forbidden in forbidden_imports)


def test_missing_credentials_prevent_factory_and_transport_calls_and_sanitize_every_surface(
    caplog: pytest.LogCaptureFixture,
) -> None:
    planted_secret = "sk-phase4-planted-secret-must-never-leak"
    calls = {"factory": 0, "transport": 0}

    class FailingTransport:
        def __init__(self, captured_secret: str) -> None:
            self.captured_secret = captured_secret

        def fetch(self, capability: DataCapability) -> object:
            calls["transport"] += 1
            raise AssertionError(self.captured_secret)

    def transport_factory() -> FailingTransport:
        calls["factory"] += 1
        return FailingTransport(planted_secret)

    profile_values = SYNTHETIC_ADAPTER_PROFILE.model_dump(mode="python")
    profile_values["synthetic"] = False
    profile_values["use_rights"] = {
        **SYNTHETIC_ADAPTER_PROFILE.use_rights.model_dump(mode="python"),
        "scope": UseRightsScope.INTERNAL_RESEARCH_ONLY,
    }
    non_synthetic_profile = AdapterProfile.model_validate(profile_values)
    adapter = CredentialGatedAdapter(
        profile=non_synthetic_profile,
        credentials_available=False,
        transport_factory=transport_factory,
    )
    result = adapter.fetch(DataCapability.OHLCV)
    rendered = " ".join(
        (
            repr(adapter),
            repr(result),
            result.model_dump_json(),
            caplog.text,
        )
    )

    assert calls == {"factory": 0, "transport": 0}
    assert result.status == "unavailable"
    assert result.reason_code is AdapterUnavailableReason.CREDENTIALS_UNAVAILABLE
    assert non_synthetic_profile.synthetic is False
    assert non_synthetic_profile.use_rights.scope is UseRightsScope.INTERNAL_RESEARCH_ONLY
    assert result.provider_id == SYNTHETIC_ADAPTER_PROFILE.provider_id
    assert result.dataset_id == SYNTHETIC_ADAPTER_PROFILE.dataset_id
    assert result.product_id == SYNTHETIC_ADAPTER_PROFILE.product_id
    assert result.entitlement_id == SYNTHETIC_ADAPTER_PROFILE.use_rights.entitlement_id
    assert result.use_rights_id == SYNTHETIC_ADAPTER_PROFILE.use_rights.use_rights_id
    assert planted_secret not in rendered


def test_transport_is_created_only_after_the_credential_gate() -> None:
    calls = {"factory": 0, "transport": 0}
    synthetic = SyntheticPointInTimeAdapter()

    class SyntheticTransport:
        def fetch(self, capability: DataCapability) -> object:
            calls["transport"] += 1
            return synthetic.fetch(capability)

    def factory() -> SyntheticTransport:
        calls["factory"] += 1
        return SyntheticTransport()

    adapter = CredentialGatedAdapter(
        profile=SYNTHETIC_ADAPTER_PROFILE,
        credentials_available=True,
        transport_factory=factory,
    )

    result = adapter.fetch(DataCapability.OHLCV)

    assert result.status == "available"
    assert calls == {"factory": 1, "transport": 1}
