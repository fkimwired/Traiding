from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    MockQualificationScenario,
    PointInTimeQualificationAdapter,
)
from fable5_data.phase13.canonical import PHASE13_FIXED_ENDPOINTS
from fable5_data.phase13.contracts import (
    PHASE13_CAPABILITY_ORDER,
    QualificationCapability,
    QualificationCheckStatus,
    QualificationReasonCode,
    QualificationRequestStatus,
)
from fable5_data.phase13.settings import TiingoQualificationAccess
from fable5_data.phase13.tiingo import TiingoCandidatePointInTimeQualificationAdapter
from pydantic import SecretStr


def _rights() -> Any:
    from fable5_data.phase13.contracts import QualificationUseRightsAttestation

    return QualificationUseRightsAttestation(
        attestation_id="phase13-test-rights-v1",
        attestation_sha256="1" * 64,
        valid_from_utc=datetime(2024, 1, 1, tzinfo=UTC),
        expires_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        storage_allowed=True,
        non_display_allowed=True,
        derived_data_allowed=True,
    )


class _Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.status = status
        self._body = body

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            return self._body
        return self._body[:amt]


class _Connection:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False

    def request(
        self,
        method: str,
        url: str,
        body: object | None = None,
        headers: dict[str, str] | None = None,
        *,
        encode_chunked: bool = False,
    ) -> None:
        del body, encode_chunked
        self.calls.append((method, url, headers or {}))

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        self.closed = True


def _adapter(connection: _Connection) -> TiingoCandidatePointInTimeQualificationAdapter:
    return TiingoCandidatePointInTimeQualificationAdapter(
        access=TiingoQualificationAccess(
            api_token=SecretStr("credential-canary"),
            rights_attestation=_rights(),
        ),
        connection_factory=lambda: connection,
        clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
    )


def test_mock_is_runtime_protocol_and_reproduces_exact_six_manifests() -> None:
    first = DeterministicMockPointInTimeQualificationAdapter()
    second = DeterministicMockPointInTimeQualificationAdapter()
    assert isinstance(first, PointInTimeQualificationAdapter)
    first_manifests = tuple(first.inspect_capability(item) for item in PHASE13_CAPABILITY_ORDER)
    second_manifests = tuple(second.inspect_capability(item) for item in PHASE13_CAPABILITY_ORDER)
    assert first_manifests == second_manifests
    assert all(item.status is QualificationCheckStatus.PASS for item in first_manifests)
    assert all(
        not evidence.external_request_performed
        for manifest in first_manifests
        for evidence in manifest.request_evidence
    )
    for forbidden in ("submit", "order", "trade", "fetch_url", "request"):
        assert not hasattr(first, forbidden)


@pytest.mark.parametrize(
    ("scenario", "capability", "reason"),
    [
        (
            MockQualificationScenario.CURRENT_UNIVERSE_SUBSTITUTION,
            QualificationCapability.POINT_IN_TIME_UNIVERSE_MEMBERSHIP,
            QualificationReasonCode.CURRENT_UNIVERSE_ONLY,
        ),
        (
            MockQualificationScenario.MISSING_DELISTING_RETURN,
            QualificationCapability.DELISTING_RETURN_SEMANTICS,
            QualificationReasonCode.DELISTING_RETURN_UNAVAILABLE,
        ),
        (
            MockQualificationScenario.ACTION_LOOKAHEAD,
            QualificationCapability.CORPORATE_ACTION_ANNOUNCEMENT_REVISION,
            QualificationReasonCode.ACTION_REVISION_INVALID,
        ),
        (
            MockQualificationScenario.RESTATEMENT_OVERWRITE,
            QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION,
            QualificationReasonCode.FUNDAMENTAL_REVISION_INVALID,
        ),
        (
            MockQualificationScenario.SCHEMA_DRIFT,
            QualificationCapability.SECURITY_MASTER_STABLE_IDENTITY,
            QualificationReasonCode.SCHEMA_DRIFT,
        ),
    ],
)
def test_mock_adversarial_scenarios_block_exact_capability(
    scenario: MockQualificationScenario,
    capability: QualificationCapability,
    reason: QualificationReasonCode,
) -> None:
    manifest = DeterministicMockPointInTimeQualificationAdapter(scenario).inspect_capability(
        capability
    )
    assert manifest.status is QualificationCheckStatus.BLOCKED
    assert manifest.reason_code is reason


def test_tiingo_eod_uses_only_exact_get_target_and_header_token() -> None:
    records = [
        {
            "date": "2020-08-28",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
            "volume": 100,
            "adjOpen": 1,
            "adjHigh": 2,
            "adjLow": 1,
            "adjClose": 2,
            "adjVolume": 400,
            "divCash": 0,
            "splitFactor": 4,
        }
    ]
    connection = _Connection(_Response(json.dumps(records).encode("utf-8")))
    manifest = _adapter(connection).inspect_capability(
        QualificationCapability.RAW_OHLCV_AVAILABILITY
    )
    assert manifest.status is QualificationCheckStatus.PASS
    assert len(connection.calls) == 1
    method, target, headers = connection.calls[0]
    assert method == "GET"
    assert target == PHASE13_FIXED_ENDPOINTS[1]["target"]
    assert headers["Authorization"] == "Token credential-canary"
    assert "credential-canary" not in target
    assert connection.closed is True
    assert manifest.request_evidence[0].status is QualificationRequestStatus.OBSERVED
    rendered = manifest.model_dump_json()
    assert "credential-canary" not in rendered
    assert '"open"' not in rendered
    assert '"close"' not in rendered


def test_tiingo_has_no_transport_for_undocumented_membership_or_delisting() -> None:
    calls = 0

    def factory() -> _Connection:
        nonlocal calls
        calls += 1
        return _Connection(_Response(b"[]"))

    adapter = TiingoCandidatePointInTimeQualificationAdapter(
        access=TiingoQualificationAccess(
            api_token=SecretStr("canary"),
            rights_attestation=_rights(),
        ),
        connection_factory=factory,
        clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
    )
    membership = adapter.inspect_capability(
        QualificationCapability.POINT_IN_TIME_UNIVERSE_MEMBERSHIP
    )
    delisting = adapter.inspect_capability(QualificationCapability.DELISTING_RETURN_SEMANTICS)
    assert calls == 0
    assert membership.status is QualificationCheckStatus.UNCOMPUTABLE
    assert membership.reason_code is QualificationReasonCode.CURRENT_UNIVERSE_ONLY
    assert delisting.status is QualificationCheckStatus.UNCOMPUTABLE
    assert delisting.reason_code is QualificationReasonCode.DELISTING_RETURN_UNAVAILABLE
