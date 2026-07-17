from __future__ import annotations

import inspect
import json
import socket
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fable5_paper.phase12.adapters import DeterministicMockPaperBrokerAdapter
from fable5_paper.phase12.alpaca import (
    MAX_RESPONSE_BYTES,
    AlpacaPaperReadOnlyAdapter,
    build_alpaca_paper_read_only_adapter,
)
from fable5_paper.phase12.canonical import (
    ALPACA_PAPER_TRADING_HOST,
    PHASE12_FIXED_ENDPOINTS,
)
from fable5_paper.phase12.contracts import ReadinessInspectionStatus
from fable5_paper.phase12.settings import (
    ALPACA_PAPER_API_KEY_ID_ENV,
    ALPACA_PAPER_SECRET_KEY_ENV,
    PaperCredentials,
    PaperCredentialSettings,
    PaperCredentialsUnavailable,
)
from pydantic import SecretStr

import scripts.capture_paper_shadow_readiness as capture

ROOT = Path(__file__).resolve().parents[3]
CLI_ARGS = [
    "--idempotency-key",
    "phase12-security-proof",
    "--confirm-paper-only-readiness",
]

assert ALPACA_PAPER_API_KEY_ID_ENV == "FABLE5_ALPACA_PAPER_API_KEY_ID"
assert ALPACA_PAPER_SECRET_KEY_ENV == "FABLE5_ALPACA_PAPER_SECRET_KEY"


class _Response:
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

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)

    def read(self, amount: int | None = None) -> bytes:
        return self.body if amount is None else self.body[:amount]

    def close(self) -> None:
        return None


class _Connection:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.requested: tuple[str, str] | None = None

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        del body, headers
        self.requested = (method, url)

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        return None


class _Factory:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[tuple[str, int, float, ssl.SSLContext]] = []
        self.connection: _Connection | None = None

    def __call__(
        self,
        host: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> _Connection:
        self.calls.append((host, port, timeout, context))
        self.connection = _Connection(self.response)
        return self.connection


def _clock():  # type: ignore[no-untyped-def]
    value = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)

    def now() -> datetime:
        nonlocal value
        result = value
        value += timedelta(milliseconds=1)
        return result

    return now


def _credentials(secret_suffix: str = "test") -> PaperCredentials:
    return PaperCredentials(
        api_key_id=SecretStr(f"paper-key-{secret_suffix}"),
        secret_key=SecretStr(f"paper-secret-{secret_suffix}"),
    )


@pytest.mark.parametrize(
    "values",
    (
        {},
        {ALPACA_PAPER_API_KEY_ID_ENV: "partial-key"},
        {ALPACA_PAPER_SECRET_KEY_ENV: "partial-secret"},
        {
            ALPACA_PAPER_API_KEY_ID_ENV: " ",
            ALPACA_PAPER_SECRET_KEY_ENV: "complete-but-paired",
        },
    ),
)
def test_missing_or_partial_credentials_fail_before_transport_factory(
    monkeypatch: pytest.MonkeyPatch,
    values: dict[str, str],
) -> None:
    for name in (ALPACA_PAPER_API_KEY_ID_ENV, ALPACA_PAPER_SECRET_KEY_ENV):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    calls = 0

    def forbidden_factory(
        host: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> _Connection:
        nonlocal calls
        del host, port, timeout, context
        calls += 1
        raise AssertionError("transport must not be constructed")

    with pytest.raises(PaperCredentialsUnavailable):
        build_alpaca_paper_read_only_adapter(
            PaperCredentialSettings(), connection_factory=forbidden_factory
        )
    assert calls == 0


@pytest.mark.parametrize(
    "values",
    (
        {},
        {ALPACA_PAPER_API_KEY_ID_ENV: "cli-partial-key"},
        {ALPACA_PAPER_SECRET_KEY_ENV: "cli-partial-secret"},
    ),
)
def test_cli_credential_gate_is_generic_and_precedes_socket_and_database(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    values: dict[str, str],
) -> None:
    for name in (ALPACA_PAPER_API_KEY_ID_ENV, ALPACA_PAPER_SECRET_KEY_ENV):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    class ForbiddenRepository:
        def __init__(self, dsn: str) -> None:
            del dsn
            raise AssertionError("database construction must follow credential validation")

    def forbidden_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("socket construction must follow credential validation")

    monkeypatch.setattr(capture, "PaperShadowReadinessRepository", ForbiddenRepository)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    assert capture.main(CLI_ARGS) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == f"{capture.FAILURE_MESSAGE}\n"
    assert not any(value and value in output.err for value in values.values())


@pytest.mark.parametrize(
    "arguments",
    (
        ["--unknown", "secret-argument"],
        [*CLI_ARGS, "--idempotency-key", "duplicate-secret"],
        [*CLI_ARGS, "--confirm-paper-only-readiness"],
        [*CLI_ARGS, "--url", "https://example.invalid"],
        [*CLI_ARGS, "--symbol", "AAPL"],
        [*CLI_ARGS, "--provider", "alpaca"],
        [*CLI_ARGS, "--quantity", "1"],
        [*CLI_ARGS, "--credential", "secret"],
        [*CLI_ARGS, "--retry", "1"],
    ),
)
def test_cli_rejects_unknown_repeated_and_forbidden_arguments_without_echo(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert capture.main(arguments) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == f"{capture.FAILURE_MESSAGE}\n"
    assert "secret-argument" not in output.err
    assert "duplicate-secret" not in output.err


def test_cli_help_is_the_only_non_capture_success_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        capture.main(["--help"])
    assert raised.value.code == 0
    output = capsys.readouterr()
    assert "PAPER ONLY" in output.out
    assert output.err == ""


def test_secret_canaries_are_absent_from_settings_repr_models_errors_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key_canary = "phase12-" + "key-canary-never-render"
    secret_canary = "phase12-" + "secret-canary-never-render"
    monkeypatch.setenv(ALPACA_PAPER_API_KEY_ID_ENV, key_canary)
    monkeypatch.setenv(ALPACA_PAPER_SECRET_KEY_ENV, secret_canary)
    settings = PaperCredentialSettings()
    credentials = settings.require_credentials()
    mock = DeterministicMockPaperBrokerAdapter().inspect_account()
    rendered = " ".join(
        (
            repr(settings),
            settings.model_dump_json(),
            repr(credentials),
            repr(PaperCredentialsUnavailable()),
            mock.evidence.model_dump_json(),
            mock.observation.model_dump_json() if mock.observation is not None else "",
        )
    )
    assert key_canary not in rendered
    assert secret_canary not in rendered


def test_mock_path_remains_operable_under_active_socket_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("mock path attempted a socket")

    monkeypatch.setattr(socket, "socket", denied_socket)
    adapter = DeterministicMockPaperBrokerAdapter()
    results = (
        adapter.inspect_account(),
        adapter.inspect_clock(),
        adapter.inspect_instrument(),
        adapter.inspect_positions(),
        adapter.inspect_open_orders(),
        adapter.inspect_latest_quote(),
    )
    assert all(item.evidence.status is ReadinessInspectionStatus.OBSERVED for item in results)


@pytest.mark.parametrize(
    "body",
    (
        b"{not-json",
        b'{"status":"ACTIVE","status":"ACTIVE"}',
        b'{"status":"ACTIVE","account_blocked":false,"trading_blocked":false,'
        b'"trade_suspended_by_user":false,"number":NaN}',
        b'{"status":"ACTIVE","account_blocked":false,"trading_blocked":false,'
        b'"trade_suspended_by_user":false,"number":"1e99999"}',
        b'\xef\xbb\xbf{"status":"ACTIVE"}',
    ),
)
def test_malformed_duplicate_nonfinite_and_unbounded_json_is_blocked(body: bytes) -> None:
    factory = _Factory(_Response(body))
    result = AlpacaPaperReadOnlyAdapter(
        _credentials(), connection_factory=factory, clock=_clock()
    ).inspect_account()
    assert result.evidence.status is ReadinessInspectionStatus.BLOCKED
    assert result.evidence.failure_reason == "response_schema_blocked"
    assert result.observation is None


def test_oversized_body_and_abusive_request_header_are_sanitized_blocked() -> None:
    oversized = _Factory(_Response(b"x" * (MAX_RESPONSE_BYTES + 1)))
    oversized_result = AlpacaPaperReadOnlyAdapter(
        _credentials(), connection_factory=oversized, clock=_clock()
    ).inspect_account()
    assert oversized_result.evidence.status is ReadinessInspectionStatus.BLOCKED
    assert oversized_result.evidence.failure_reason == "transport_unavailable"

    header = _Factory(
        _Response(
            b"{}",
            headers={"X-Request-ID": "bad\r\nheader"},
        )
    )
    header_result = AlpacaPaperReadOnlyAdapter(
        _credentials(), connection_factory=header, clock=_clock()
    ).inspect_account()
    assert header_result.evidence.status is ReadinessInspectionStatus.BLOCKED
    assert header_result.evidence.failure_reason == "transport_unavailable"
    assert header_result.evidence.request_id is None


def test_proxy_environment_is_ignored_and_only_fixed_host_is_representable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    body = json.dumps(
        {
            "status": "ACTIVE",
            "account_blocked": False,
            "trading_blocked": False,
            "trade_suspended_by_user": False,
        }
    ).encode()
    factory = _Factory(_Response(body))
    adapter = AlpacaPaperReadOnlyAdapter(_credentials(), connection_factory=factory, clock=_clock())

    result = adapter.inspect_account()

    assert result.evidence.status is ReadinessInspectionStatus.OBSERVED
    assert factory.calls[0][0] == ALPACA_PAPER_TRADING_HOST
    assert factory.connection is not None
    assert factory.connection.requested == ("GET", PHASE12_FIXED_ENDPOINTS[0]["target"])
    signature = inspect.signature(AlpacaPaperReadOnlyAdapter)
    forbidden = {"url", "host", "port", "scheme", "method", "path", "query", "provider"}
    assert not (set(signature.parameters) & forbidden)


def test_phase12_source_has_no_mutation_sdk_or_arbitrary_origin_configuration() -> None:
    root = ROOT / "services/paper/src/fable5_paper/phase12"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    lowered = combined.casefold()
    for forbidden in (
        "import requests",
        "import httpx",
        "import alpaca",
        "submit_order",
        "replace_order",
        "cancel_order",
        "close_position",
        "base_url",
    ):
        assert forbidden not in lowered
