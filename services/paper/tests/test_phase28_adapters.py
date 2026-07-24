from __future__ import annotations

import json
import ssl
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fable5_paper.phase12.settings import PaperCredentials
from fable5_paper.phase28 import alpaca as alpaca_module
from fable5_paper.phase28.alpaca import (
    AlpacaIexObservationOnlyAdapter,
    ExactUseReviewUnavailable,
    build_alpaca_iex_observation_only_adapter,
)
from fable5_paper.phase28.canonical import (
    PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    PHASE28_FIXED_ENDPOINTS,
)
from fable5_paper.phase28.contracts import InspectionStatus
from fable5_paper.phase28.settings import Phase28PaperCredentialSettings
from fable5_paper.phase28.workflow import Phase28ObservationWorkflow
from pydantic import SecretStr, ValidationError

NOW = datetime(2026, 7, 24, 16, 0, tzinfo=UTC)
KEY_CANARY = "KEY_CANARY_PHASE28"
SECRET_CANARY = "SECRET_CANARY_PHASE28"


@pytest.fixture(autouse=True)
def _freeze_exact_use_review_currentness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alpaca_module, "_system_utc_now", lambda: NOW)


class _Response:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        request_id: str | None = "request-canary-123",
    ) -> None:
        self.status = status
        self._body = body
        self._request_id = request_id
        self.closed = False

    def getheader(self, name: str, default: str | None = None) -> str | None:
        if name == "Content-Type":
            return "application/json"
        if name == "Content-Length":
            return str(len(self._body))
        if name == "X-Request-ID":
            return self._request_id
        return default

    def read(self, amount: int | None = None) -> bytes:
        assert amount is not None
        return self._body[:amount]

    def close(self) -> None:
        self.closed = True


class _Connection:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.requests: list[tuple[str, str, bytes | None, dict[str, str] | None]] = []
        self.closed = False

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.requests.append((method, url, body, headers))

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        self.closed = True


def _credentials() -> PaperCredentials:
    return PaperCredentials(
        api_key_id=SecretStr(KEY_CANARY),
        secret_key=SecretStr(SECRET_CANARY),
    )


def _asset_body(
    *,
    symbol: str = "AAPL",
    status: str = "active",
    extra: dict[str, object] | None = None,
) -> bytes:
    payload: dict[str, object] = {
        "id": "b0b6dd9d-8b9b-52ba-a39b-36bd3d5b2024",
        "class": "us_equity",
        "exchange": "NASDAQ",
        "symbol": symbol,
        "name": f"{symbol} instrument",
        "status": status,
        "tradable": True,
    }
    payload.update(extra or {})
    return json.dumps(payload).encode()


def _adapter(response: _Response) -> tuple[AlpacaIexObservationOnlyAdapter, _Connection]:
    connection = _Connection(response)

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        assert (host, port, timeout) == ("paper-api.alpaca.markets", 443, 5.0)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        return connection

    ticks = iter((NOW, NOW + timedelta(milliseconds=1)))
    return (
        AlpacaIexObservationOnlyAdapter(
            _credentials(),
            exact_use_review_confirmed=True,
            connection_factory=factory,
            clock=lambda: next(ticks),
        ),
        connection,
    )


def _data_adapter(response: _Response) -> AlpacaIexObservationOnlyAdapter:
    connection = _Connection(response)

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        assert (host, port, timeout) == ("data.alpaca.markets", 443, 5.0)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        return connection

    ticks = iter((NOW, NOW + timedelta(milliseconds=1)))
    return AlpacaIexObservationOnlyAdapter(
        _credentials(),
        exact_use_review_confirmed=True,
        connection_factory=factory,
        clock=lambda: next(ticks),
    )


def test_asset_transport_is_exact_get_and_request_id_is_hash_only() -> None:
    adapter, connection = _adapter(_Response(_asset_body()))

    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.OBSERVED
    assert connection.requests[0][:3] == ("GET", "/v2/assets/AAPL", None)
    assert connection.requests[0][3] == {
        "Accept": "application/json",
        "APCA-API-KEY-ID": KEY_CANARY,
        "APCA-API-SECRET-KEY": SECRET_CANARY,
    }
    dumped = json.dumps(result.evidence.model_dump(mode="json"), sort_keys=True)
    assert "request-canary-123" not in dumped
    assert KEY_CANARY not in dumped
    assert SECRET_CANARY not in dumped
    assert result.evidence.request_id_sha256 is not None
    assert connection.closed and connection.response.closed


@pytest.mark.parametrize(
    "body",
    [
        _asset_body(status="ACTIVE"),
        _asset_body(extra={"unexpected": "schema drift"}),
        _asset_body(extra={"name": "bad\u0001name"}),
        _asset_body(extra={"maintenance_margin_requirement": "NaN"}),
        _asset_body(extra={"maintenance_margin_requirement": "1e100000"}),
        _asset_body(extra={"class": "crypto"}),
    ],
)
def test_asset_schema_anomalies_fail_closed(body: bytes) -> None:
    adapter, _ = _adapter(_Response(body))

    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "response_schema_blocked"
    assert result.payload is None


def test_provider_models_and_validation_errors_hide_raw_values() -> None:
    raw_price_canary = "193.77"
    bar = alpaca_module._Bar.model_validate(
        {
            "t": "2026-07-24T16:00:00Z",
            "o": raw_price_canary,
            "h": "194",
            "l": "193",
            "c": "193.5",
            "v": "100",
        }
    )

    assert raw_price_canary not in repr(bar)
    assert raw_price_canary not in str(bar)

    invalid_canary = "RAW_PROVIDER_VALUE_CANARY"
    with pytest.raises(ValidationError) as caught:
        alpaca_module._Bar.model_validate(
            {
                "t": "2026-07-24T16:00:00Z",
                "o": invalid_canary,
                "h": "194",
                "l": "193",
                "c": "193.5",
                "v": "100",
            }
        )
    assert invalid_canary not in str(caught.value)


def test_redirect_is_blocked_without_following() -> None:
    adapter, connection = _adapter(_Response(b"{}", status=302))

    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "transport_redirect_blocked"
    assert len(connection.requests) == 1


def test_naive_provider_timestamp_fails_closed() -> None:
    bar = {
        "t": "2026-07-24T16:00:00",
        "o": "100",
        "h": "103",
        "l": "99",
        "c": "102",
        "v": "1000",
    }
    body = json.dumps(
        {"bars": {symbol: bar for symbol in ("AAPL", "MSFT", "SPY")}, "currency": "USD"}
    ).encode()
    result = _data_adapter(_Response(body)).inspect_latest_bars()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "response_schema_blocked"


def test_workflow_performs_exact_six_gets_and_emits_sanitized_external_evidence() -> None:
    bar = {
        "t": "2026-07-24T15:59:50Z",
        "o": "100",
        "h": "103",
        "l": "99",
        "c": "102",
        "v": "1000",
        "n": 10,
        "vw": "101",
    }
    quote = {
        "t": "2026-07-24T15:59:55Z",
        "ap": "102",
        "bp": "101",
        "as": "10",
        "bs": "10",
    }
    trade = {
        "t": "2026-07-24T15:59:55Z",
        "p": "101.5",
        "s": "1",
    }
    previous = {
        **bar,
        "t": "2026-07-23T20:00:00Z",
        "o": "98",
        "h": "100",
        "l": "97",
        "c": "99",
    }
    bodies = [_asset_body(symbol=symbol) for symbol in ("AAPL", "MSFT", "SPY")] + [
        json.dumps(
            {"bars": {symbol: bar for symbol in ("AAPL", "MSFT", "SPY")}, "currency": "USD"}
        ).encode(),
        json.dumps(
            {
                "quotes": {symbol: quote for symbol in ("AAPL", "MSFT", "SPY")},
                "currency": "USD",
            }
        ).encode(),
        json.dumps(
            {
                symbol: {
                    "latestTrade": trade,
                    "latestQuote": quote,
                    "minuteBar": bar,
                    "dailyBar": bar,
                    "prevDailyBar": previous,
                }
                for symbol in ("AAPL", "MSFT", "SPY")
            }
        ).encode(),
    ]
    connections: list[_Connection] = []

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        del host, port, timeout, context
        connection = _Connection(
            _Response(bodies[len(connections)], request_id=f"request-{len(connections) + 1}")
        )
        connections.append(connection)
        return connection

    tick_index = 0

    def transport_clock() -> datetime:
        nonlocal tick_index
        value = NOW + timedelta(milliseconds=tick_index * 10)
        tick_index += 1
        return value

    adapter = AlpacaIexObservationOnlyAdapter(
        _credentials(),
        exact_use_review_confirmed=True,
        connection_factory=factory,
        clock=transport_clock,
    )
    artifact = Phase28ObservationWorkflow(
        adapter=adapter,
        code_version_git_sha="e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e",
        clock=lambda: NOW + timedelta(seconds=1),
    ).run()

    assert [
        (connection.requests[0][0], connection.requests[0][1]) for connection in connections
    ] == [(endpoint.method, endpoint.target) for endpoint in PHASE28_FIXED_ENDPOINTS]
    assert all(item.external_request_performed for item in artifact.inspections)
    assert all(item.http_status == 200 for item in artifact.inspections)
    assert artifact.exact_use_review_confirmed_for_external_run is True
    rendered = json.dumps(artifact.model_dump(mode="json"), sort_keys=True)
    for canary in (KEY_CANARY, SECRET_CANARY, "101.5", '"ap"', '"bp"'):
        assert canary not in rendered


def test_connection_failure_does_not_claim_request_performed() -> None:
    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext) -> _Connection:
        del host, port, timeout, context
        raise OSError("transport canary")

    adapter = AlpacaIexObservationOnlyAdapter(
        _credentials(),
        exact_use_review_confirmed=True,
        connection_factory=factory,
        clock=lambda: NOW,
    )
    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.external_request_performed is False
    assert result.evidence.http_status is None
    assert result.evidence.response_sha256 is None


def test_fixed_endpoint_registry_is_immutable() -> None:
    with pytest.raises(AttributeError):
        PHASE28_FIXED_ENDPOINTS[0].host = "api.alpaca.markets"  # type: ignore[misc]
    assert [item.method for item in PHASE28_FIXED_ENDPOINTS] == ["GET"] * 6
    assert [item.host for item in PHASE28_FIXED_ENDPOINTS] == [
        "paper-api.alpaca.markets",
        "paper-api.alpaca.markets",
        "paper-api.alpaca.markets",
        "data.alpaca.markets",
        "data.alpaca.markets",
        "data.alpaca.markets",
    ]


def test_expired_exact_use_review_blocks_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLE5_ALPACA_PAPER_API_KEY_ID", KEY_CANARY)
    monkeypatch.setenv("FABLE5_ALPACA_PAPER_SECRET_KEY", SECRET_CANARY)
    called = False

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        nonlocal called
        del host, port, timeout, context
        called = True
        raise AssertionError

    monkeypatch.setattr(
        alpaca_module,
        "_system_utc_now",
        lambda: PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    )
    with pytest.raises(ExactUseReviewUnavailable):
        build_alpaca_iex_observation_only_adapter(
            Phase28PaperCredentialSettings(),
            exact_use_review_confirmed=True,
            connection_factory=cast(object, factory),
        )

    assert called is False


def test_direct_adapter_construction_cannot_bypass_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        alpaca_module,
        "_system_utc_now",
        lambda: PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    )
    with pytest.raises(ExactUseReviewUnavailable):
        AlpacaIexObservationOnlyAdapter(
            _credentials(),
            exact_use_review_confirmed=True,
        )


def test_adapter_created_before_expiry_cannot_connect_after_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = [NOW]
    monkeypatch.setattr(alpaca_module, "_system_utc_now", lambda: current[0])
    called = False

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        nonlocal called
        del host, port, timeout, context
        called = True
        raise AssertionError

    adapter = AlpacaIexObservationOnlyAdapter(
        _credentials(),
        exact_use_review_confirmed=True,
        connection_factory=cast(object, factory),
        clock=lambda: NOW,
    )
    current[0] = PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC

    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "exact_use_review_unavailable"
    assert result.evidence.external_request_performed is False
    assert called is False


def test_deadline_crossed_during_connection_creation_blocks_request_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = [NOW]
    monkeypatch.setattr(alpaca_module, "_system_utc_now", lambda: current[0])
    connection = _Connection(_Response(_asset_body()))

    def factory(host: str, port: int, timeout: float, context: ssl.SSLContext):
        del host, port, timeout, context
        current[0] = PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC
        return connection

    adapter = AlpacaIexObservationOnlyAdapter(
        _credentials(),
        exact_use_review_confirmed=True,
        connection_factory=cast(object, factory),
        clock=lambda: NOW,
    )

    result = adapter.inspect_asset_aapl()

    assert result.evidence.status is InspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "exact_use_review_unavailable"
    assert result.evidence.external_request_performed is False
    assert connection.requests == []
    assert connection.closed


def test_external_adapter_has_no_mutation_method() -> None:
    public = {name for name in dir(AlpacaIexObservationOnlyAdapter) if not name.startswith("_")}
    assert public == {
        "exact_use_review_confirmed_for_external_run",
        "inspect_asset_aapl",
        "inspect_asset_msft",
        "inspect_asset_spy",
        "inspect_latest_bars",
        "inspect_latest_quotes",
        "inspect_snapshots",
        "source_kind",
        "transport_profile_sha256",
    }
