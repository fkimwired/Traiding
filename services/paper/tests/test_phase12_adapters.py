from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fable5_paper.phase12.adapters import (
    DeterministicMockPaperBrokerAdapter,
    PaperBrokerAdapter,
)
from fable5_paper.phase12.alpaca import AlpacaPaperReadOnlyAdapter
from fable5_paper.phase12.canonical import PHASE12_FIXED_ENDPOINTS
from fable5_paper.phase12.contracts import (
    PHASE12_INSPECTION_ORDER,
    ReadinessInspectionStatus,
    ReadinessSourceKind,
)
from fable5_paper.phase12.settings import PaperCredentials
from pydantic import SecretStr


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            **(headers or {}),
        }
        self.closed = False

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)

    def read(self, amount: int | None = None) -> bytes:
        return self.body if amount is None else self.body[:amount]

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request_record: tuple[str, str, dict[str, str]] | None = None
        self.closed = False

    def __repr__(self) -> str:
        return "FakeConnection(sanitized=True)"

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        assert body is None
        self.request_record = (method, url, dict(headers or {}))

    def getresponse(self) -> FakeResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


class RecordingConnectionFactory:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, int, float, ssl.SSLContext, FakeConnection]] = []

    def __call__(
        self,
        host: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> FakeConnection:
        connection = FakeConnection(self.responses.pop(0))
        self.calls.append((host, port, timeout, context, connection))
        return connection


def _json(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def successful_responses() -> list[FakeResponse]:
    return [
        FakeResponse(
            _json(
                {
                    "status": "ACTIVE",
                    "account_blocked": False,
                    "trading_blocked": False,
                    "trade_suspended_by_user": False,
                }
            ),
            headers={"X-Request-ID": "phase12-account"},
        ),
        FakeResponse(
            _json(
                {
                    "is_open": True,
                    "timestamp": "2024-01-02T15:00:00Z",
                    "next_open": "2024-01-03T14:30:00Z",
                    "next_close": "2024-01-02T21:00:00Z",
                }
            )
        ),
        FakeResponse(
            _json(
                {
                    "id": "b0b6dd9d-8b9b-52ba-a39b-36bd3d5b2024",
                    "exchange": "NASDAQ",
                    "symbol": "AAPL",
                    "status": "active",
                    "tradable": True,
                }
            )
        ),
        FakeResponse(b"[]"),
        FakeResponse(b"[]"),
        FakeResponse(
            _json(
                {
                    "symbol": "AAPL",
                    "quote": {
                        "ap": "101.01",
                        "bp": "101.00",
                        "t": "2024-01-02T15:00:00Z",
                    },
                }
            )
        ),
    ]


def _clock() -> Callable[[], datetime]:
    current = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)

    def now() -> datetime:
        nonlocal current
        value = current
        current += timedelta(milliseconds=1)
        return value

    return now


def _credentials() -> PaperCredentials:
    return PaperCredentials(
        api_key_id=SecretStr("paper-key-test"),
        secret_key=SecretStr("paper-secret-test"),
    )


def test_mock_and_external_implement_the_same_read_only_protocol() -> None:
    mock = DeterministicMockPaperBrokerAdapter()
    external = AlpacaPaperReadOnlyAdapter(
        _credentials(), connection_factory=RecordingConnectionFactory(successful_responses())
    )

    assert isinstance(mock, PaperBrokerAdapter)
    assert isinstance(external, PaperBrokerAdapter)
    assert mock.source_kind is ReadinessSourceKind.DETERMINISTIC_MOCK
    assert external.source_kind is ReadinessSourceKind.ALPACA_PAPER_READ_ONLY
    for adapter in (mock, external):
        for forbidden in ("submit", "replace", "cancel", "liquidate", "close_position"):
            assert not hasattr(adapter, forbidden)


def test_external_adapter_performs_exactly_six_ordered_fixed_https_gets() -> None:
    factory = RecordingConnectionFactory(successful_responses())
    adapter = AlpacaPaperReadOnlyAdapter(
        _credentials(),
        connection_factory=factory,
        clock=_clock(),
    )

    inspections = (
        adapter.inspect_account(),
        adapter.inspect_clock(),
        adapter.inspect_instrument(),
        adapter.inspect_positions(),
        adapter.inspect_open_orders(),
        adapter.inspect_latest_quote(),
    )

    assert tuple(item.evidence.code for item in inspections) == PHASE12_INSPECTION_ORDER
    assert all(item.evidence.status is ReadinessInspectionStatus.OBSERVED for item in inspections)
    assert all(item.observation is not None for item in inspections)
    assert len(factory.calls) == 6
    for endpoint, (host, port, timeout, context, connection) in zip(
        PHASE12_FIXED_ENDPOINTS, factory.calls, strict=True
    ):
        assert (host, port) == (endpoint["host"], 443)
        assert timeout == 5.0
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert connection.request_record is not None
        method, target, headers = connection.request_record
        assert (method, target) == ("GET", endpoint["target"])
        assert set(headers) == {"Accept", "APCA-API-KEY-ID", "APCA-API-SECRET-KEY"}
        assert connection.closed is True
        assert connection.response.closed is True


def test_mock_inspections_are_byte_stable_and_claim_no_external_request() -> None:
    first = DeterministicMockPaperBrokerAdapter()
    second = DeterministicMockPaperBrokerAdapter()
    methods = (
        "inspect_account",
        "inspect_clock",
        "inspect_instrument",
        "inspect_positions",
        "inspect_open_orders",
        "inspect_latest_quote",
    )

    first_results = [getattr(first, method)() for method in methods]
    second_results = [getattr(second, method)() for method in methods]

    assert first_results == second_results
    assert all(not item.evidence.external_request_performed for item in first_results)
    assert all(item.evidence.http_status is None for item in first_results)


def test_redirect_is_blocked_and_never_followed() -> None:
    factory = RecordingConnectionFactory(
        [FakeResponse(b"{}", status=302, headers={"Location": "https://example.invalid/next"})]
    )
    adapter = AlpacaPaperReadOnlyAdapter(_credentials(), connection_factory=factory, clock=_clock())

    result = adapter.inspect_account()

    assert result.evidence.status is ReadinessInspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "transport_redirect_blocked"
    assert result.observation is None
    assert len(factory.calls) == 1


def test_unknown_response_field_and_duplicate_key_fail_closed() -> None:
    unknown = FakeResponse(
        _json(
            {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
                "trade_suspended_by_user": False,
                "unexpected": "schema-drift",
            }
        )
    )
    duplicate = FakeResponse(
        b'{"status":"ACTIVE","status":"ACTIVE","account_blocked":false,'
        b'"trading_blocked":false,"trade_suspended_by_user":false}'
    )
    factory = RecordingConnectionFactory([unknown, duplicate])
    adapter = AlpacaPaperReadOnlyAdapter(_credentials(), connection_factory=factory, clock=_clock())

    first = adapter.inspect_account()
    second = adapter.inspect_account()

    assert first.evidence.failure_reason == "response_schema_blocked"
    assert second.evidence.failure_reason == "response_schema_blocked"
    assert first.observation is second.observation is None


def test_nonempty_inventory_is_sanitized_to_count_and_hash_only() -> None:
    payload: list[dict[str, Any]] = [{"sensitive": "not-retained"}]
    factory = RecordingConnectionFactory([FakeResponse(_json(payload))])
    adapter = AlpacaPaperReadOnlyAdapter(_credentials(), connection_factory=factory, clock=_clock())

    result = adapter.inspect_positions()

    assert result.observation is not None
    assert result.observation.item_count == 1  # type: ignore[union-attr]
    assert "sensitive" not in result.observation.model_dump_json()
