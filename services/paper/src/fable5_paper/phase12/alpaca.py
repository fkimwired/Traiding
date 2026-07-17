"""Sole external Phase 12 adapter: fixed-origin Alpaca paper/data HTTPS reads."""

from __future__ import annotations

import http.client
import json
import re
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, NoReturn, Protocol, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fable5_paper.phase12.adapters import (
    PaperBrokerInspection,
    build_account_observation,
    build_clock_observation,
    build_inspection_evidence,
    build_instrument_observation,
    build_inventory_observation,
    build_quote_observation,
)
from fable5_paper.phase12.canonical import (
    PHASE12_FIXED_ENDPOINTS,
    PHASE12_TRANSPORT_PROFILE_SHA256,
    raw_response_sha256,
)
from fable5_paper.phase12.contracts import (
    PaperAccountObservation,
    PaperClockObservation,
    PaperInstrumentObservation,
    PaperInventoryObservation,
    PaperQuoteObservation,
    ReadinessInspectionCode,
    ReadinessInspectionStatus,
    ReadinessObservation,
    ReadinessSourceKind,
)
from fable5_paper.phase12.settings import PaperCredentials, PaperCredentialSettings

MAX_RESPONSE_BYTES = 256 * 1024
MAX_NUMERIC_COEFFICIENT_DIGITS = 128
MAX_NUMERIC_ABS_EXPONENT = 1_000
HTTPS_TIMEOUT_SECONDS = 5.0
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NUMERIC_TEXT = re.compile(r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?\Z")


class _StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _AccountResponse(_StrictResponse):
    status: str = Field(min_length=1, max_length=64)
    account_blocked: bool
    trading_blocked: bool
    trade_suspended_by_user: bool
    transfers_blocked: bool | None = None
    id: str | None = None
    account_number: str | None = None
    currency: str | None = None
    pattern_day_trader: bool | None = None
    shorting_enabled: bool | None = None
    created_at: datetime | None = None
    crypto_status: str | None = None
    buying_power: Decimal | None = None
    regt_buying_power: Decimal | None = None
    daytrading_buying_power: Decimal | None = None
    effective_buying_power: Decimal | None = None
    non_marginable_buying_power: Decimal | None = None
    bod_dtbp: Decimal | None = None
    cash: Decimal | None = None
    accrued_fees: Decimal | None = None
    pending_transfer_in: Decimal | None = None
    pending_transfer_out: Decimal | None = None
    portfolio_value: Decimal | None = None
    multiplier: Decimal | None = None
    equity: Decimal | None = None
    last_equity: Decimal | None = None
    long_market_value: Decimal | None = None
    short_market_value: Decimal | None = None
    initial_margin: Decimal | None = None
    maintenance_margin: Decimal | None = None
    last_maintenance_margin: Decimal | None = None
    sma: Decimal | None = None
    daytrade_count: int | None = None
    balance_asof: str | None = None
    crypto_tier: int | None = None
    intraday_adjustments: Decimal | None = None
    pending_reg_taf_fees: Decimal | None = None


class _ClockResponse(_StrictResponse):
    is_open: bool
    timestamp: datetime
    next_open: datetime
    next_close: datetime


class _AssetResponse(_StrictResponse):
    id: UUID
    asset_class: str | None = Field(default=None, alias="class")
    exchange: str = Field(min_length=1, max_length=64)
    symbol: Literal["AAPL"]
    status: str = Field(min_length=1, max_length=64)
    tradable: bool
    name: str | None = None
    marginable: bool | None = None
    maintenance_margin_requirement: Decimal | None = None
    shortable: bool | None = None
    easy_to_borrow: bool | None = None
    fractionable: bool | None = None
    attributes: list[str] | None = None
    borrow_status: str | None = None
    margin_requirement_long: Decimal | None = None
    margin_requirement_short: Decimal | None = None
    overnight_halted: bool | None = None
    overnight_tradable: bool | None = None


class _QuotePayload(_StrictResponse):
    ap: Decimal
    bp: Decimal
    t: datetime
    ask_size: Decimal | None = Field(default=None, alias="as")
    bid_size: Decimal | None = Field(default=None, alias="bs")
    ax: str | None = None
    bx: str | None = None
    c: list[str] | None = None
    z: str | None = None


class _LatestQuoteResponse(_StrictResponse):
    symbol: Literal["AAPL"]
    quote: _QuotePayload


class _HttpsResponse(Protocol):
    status: int

    def getheader(self, name: str, default: str | None = None) -> str | None: ...

    def read(self, amount: int | None = None) -> bytes: ...

    def close(self) -> None: ...


class _HttpsConnection(Protocol):
    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None: ...

    def getresponse(self) -> _HttpsResponse: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[[str, int, float, ssl.SSLContext], _HttpsConnection]
Clock = Callable[[], datetime]


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _default_connection_factory(
    host: str,
    port: int,
    timeout: float,
    context: ssl.SSLContext,
) -> _HttpsConnection:
    return cast(
        _HttpsConnection,
        http.client.HTTPSConnection(host=host, port=port, timeout=timeout, context=context),
    )


class _TransportFailure(RuntimeError):
    def __init__(
        self,
        reason: str,
        *,
        started_at_utc: datetime,
        completed_at_utc: datetime,
        http_status: int | None = None,
        request_id: str | None = None,
        response_sha256: str | None = None,
    ) -> None:
        super().__init__("paper-readiness transport was blocked")
        self.reason = reason
        self.started_at_utc = started_at_utc
        self.completed_at_utc = completed_at_utc
        self.http_status = http_status
        self.request_id = request_id
        self.response_sha256 = response_sha256


class _TransportResponse:
    __slots__ = (
        "body",
        "completed_at_utc",
        "http_status",
        "request_id",
        "response_sha256",
        "started_at_utc",
    )

    def __init__(
        self,
        *,
        body: bytes,
        started_at_utc: datetime,
        completed_at_utc: datetime,
        http_status: int,
        request_id: str | None,
        response_sha256: str,
    ) -> None:
        self.body = body
        self.started_at_utc = started_at_utc
        self.completed_at_utc = completed_at_utc
        self.http_status = http_status
        self.request_id = request_id
        self.response_sha256 = response_sha256

    def __repr__(self) -> str:
        return "_TransportResponse(sanitized=True)"


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("transport clock must be timezone-aware")
    return value.astimezone(UTC)


def _safe_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    if _REQUEST_ID.fullmatch(value) is None:
        raise ValueError("request identifier is invalid")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    del value
    raise ValueError("non-finite response number")


def _bounded_decimal(value: str) -> Decimal:
    coefficient, _, exponent_text = value.lower().partition("e")
    digits = coefficient.lstrip("+-").replace(".", "").lstrip("0") or "0"
    if len(digits) > MAX_NUMERIC_COEFFICIENT_DIGITS:
        raise ValueError("response number is too large")
    try:
        exponent = int(exponent_text or "0")
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("response number is invalid") from None
    if not parsed.is_finite() or abs(exponent) > MAX_NUMERIC_ABS_EXPONENT:
        raise ValueError("response number is outside bounds")
    return parsed


def _guard_strings(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str):
            if _CONTROL_CHARACTERS.search(item):
                raise ValueError("response contains a control character")
            if _NUMERIC_TEXT.fullmatch(item):
                _bounded_decimal(item)


def _decode_json(body: bytes) -> object:
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError("response BOM is forbidden")
    text = body.decode("utf-8", errors="strict")
    decoded = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_float=_bounded_decimal,
        parse_int=_bounded_decimal,
        parse_constant=_reject_constant,
    )
    _guard_strings(decoded)
    return decoded


class _FixedAlpacaPaperTransport:
    def __init__(
        self,
        credentials: PaperCredentials,
        *,
        connection_factory: ConnectionFactory,
        clock: Clock,
    ) -> None:
        self._credentials = credentials
        self._connection_factory = connection_factory
        self._clock = clock

    def fetch(self, code: ReadinessInspectionCode) -> _TransportResponse:
        if not isinstance(code, ReadinessInspectionCode):
            raise TypeError("inspection code is not in the frozen registry")
        ordinal = tuple(ReadinessInspectionCode).index(code)
        endpoint = PHASE12_FIXED_ENDPOINTS[ordinal]
        started = _normalize_utc(self._clock())
        connection: _HttpsConnection | None = None
        response: _HttpsResponse | None = None
        try:
            context = ssl.create_default_context()
            if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
                raise ValueError("TLS verification is unavailable")
            connection = self._connection_factory(
                str(endpoint["host"]),
                int(str(endpoint["port"])),
                HTTPS_TIMEOUT_SECONDS,
                context,
            )
            connection.request(
                "GET",
                str(endpoint["target"]),
                headers={
                    "Accept": "application/json",
                    "APCA-API-KEY-ID": self._credentials.api_key_id.get_secret_value(),
                    "APCA-API-SECRET-KEY": self._credentials.secret_key.get_secret_value(),
                },
            )
            response = connection.getresponse()
            content_type = response.getheader("Content-Type")
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError:
                    raise ValueError("response length is invalid") from None
                if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
                    raise ValueError("response body is oversized")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError("response body is oversized")
            completed = _normalize_utc(self._clock())
            response_hash = raw_response_sha256(body)
            request_id = _safe_request_id(response.getheader("X-Request-ID"))
            if content_type is None or content_type.split(";", 1)[0].strip().casefold() != (
                "application/json"
            ):
                raise _TransportFailure(
                    "response_content_type_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id=request_id,
                    response_sha256=response_hash,
                )
            if 300 <= response.status <= 399:
                raise _TransportFailure(
                    "transport_redirect_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id=request_id,
                    response_sha256=response_hash,
                )
            if response.status != 200:
                raise _TransportFailure(
                    "transport_http_status_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id=request_id,
                    response_sha256=response_hash,
                )
            return _TransportResponse(
                body=body,
                started_at_utc=started,
                completed_at_utc=completed,
                http_status=response.status,
                request_id=request_id,
                response_sha256=response_hash,
            )
        except _TransportFailure:
            raise
        except Exception:
            completed = _normalize_utc(self._clock())
            raise _TransportFailure(
                "transport_unavailable",
                started_at_utc=started,
                completed_at_utc=completed,
            ) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass


Parser = Callable[[object, datetime, str], ReadinessObservation]


def _parse_account(
    decoded: object, received: datetime, response_hash: str
) -> PaperAccountObservation:
    del received, response_hash
    response = _AccountResponse.model_validate(decoded)
    return build_account_observation(
        status=response.status,
        account_blocked=response.account_blocked,
        trading_blocked=response.trading_blocked,
        trade_suspended_by_user=response.trade_suspended_by_user,
    )


def _parse_clock(decoded: object, received: datetime, response_hash: str) -> PaperClockObservation:
    del received, response_hash
    response = _ClockResponse.model_validate(decoded)
    return build_clock_observation(
        is_open=response.is_open,
        provider_timestamp_utc=response.timestamp,
        next_open_utc=response.next_open,
        next_close_utc=response.next_close,
    )


def _parse_instrument(
    decoded: object, received: datetime, response_hash: str
) -> PaperInstrumentObservation:
    del received, response_hash
    response = _AssetResponse.model_validate(decoded)
    return build_instrument_observation(
        asset_id=response.id,
        exchange=response.exchange,
        status=response.status,
        active=response.status.casefold() == "active",
        tradable=response.tradable,
    )


def _parse_inventory(kind: Literal["POSITIONS", "OPEN_ORDERS"]) -> Parser:
    def parse(decoded: object, received: datetime, response_hash: str) -> PaperInventoryObservation:
        del received
        if not isinstance(decoded, list):
            raise ValueError("inventory response must be a JSON array")
        return build_inventory_observation(
            inventory_kind=kind,
            item_count=len(decoded),
            inventory_sha256=response_hash,
        )

    return parse


def _parse_quote(decoded: object, received: datetime, response_hash: str) -> PaperQuoteObservation:
    del response_hash
    response = _LatestQuoteResponse.model_validate(decoded)
    bid_valid = response.quote.bp.is_finite() and response.quote.bp > 0
    ask_valid = response.quote.ap.is_finite() and response.quote.ap > 0
    return build_quote_observation(
        event_time_utc=response.quote.t,
        received_at_utc=received,
        bid_price_valid=bid_valid,
        ask_price_valid=ask_valid,
        non_crossed=bid_valid and ask_valid and response.quote.ap >= response.quote.bp,
    )


class AlpacaPaperReadOnlyAdapter:
    """Exactly six fixed paper/data reads with no generic or mutating public method."""

    def __init__(
        self,
        credentials: PaperCredentials,
        *,
        connection_factory: ConnectionFactory = _default_connection_factory,
        clock: Clock = _system_utc_now,
    ) -> None:
        self._transport = _FixedAlpacaPaperTransport(
            credentials,
            connection_factory=connection_factory,
            clock=clock,
        )

    @classmethod
    def from_credentials(
        cls,
        credentials: PaperCredentials,
        *,
        connection_factory: ConnectionFactory = _default_connection_factory,
        clock: Clock = _system_utc_now,
    ) -> AlpacaPaperReadOnlyAdapter:
        return cls(credentials, connection_factory=connection_factory, clock=clock)

    @property
    def source_kind(self) -> ReadinessSourceKind:
        return ReadinessSourceKind.ALPACA_PAPER_READ_ONLY

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE12_TRANSPORT_PROFILE_SHA256

    def _inspect(
        self,
        ordinal: int,
        code: ReadinessInspectionCode,
        parser: Parser,
    ) -> PaperBrokerInspection:
        try:
            transport = self._transport.fetch(code)
        except _TransportFailure as exc:
            return PaperBrokerInspection(
                evidence=build_inspection_evidence(
                    ordinal=ordinal,
                    code=code,
                    status=ReadinessInspectionStatus.BLOCKED,
                    external_request_performed=True,
                    request_started_at_utc=exc.started_at_utc,
                    request_completed_at_utc=exc.completed_at_utc,
                    http_status=exc.http_status,
                    request_id=exc.request_id,
                    response_sha256=exc.response_sha256,
                    failure_reason=exc.reason,
                ),
                observation=None,
            )
        try:
            decoded = _decode_json(transport.body)
            observation = parser(decoded, transport.completed_at_utc, transport.response_sha256)
        except (TypeError, ValueError, ValidationError, UnicodeDecodeError, json.JSONDecodeError):
            return PaperBrokerInspection(
                evidence=build_inspection_evidence(
                    ordinal=ordinal,
                    code=code,
                    status=ReadinessInspectionStatus.BLOCKED,
                    external_request_performed=True,
                    request_started_at_utc=transport.started_at_utc,
                    request_completed_at_utc=transport.completed_at_utc,
                    http_status=transport.http_status,
                    request_id=transport.request_id,
                    response_sha256=transport.response_sha256,
                    failure_reason="response_schema_blocked",
                ),
                observation=None,
            )
        return PaperBrokerInspection(
            evidence=build_inspection_evidence(
                ordinal=ordinal,
                code=code,
                status=ReadinessInspectionStatus.OBSERVED,
                external_request_performed=True,
                request_started_at_utc=transport.started_at_utc,
                request_completed_at_utc=transport.completed_at_utc,
                http_status=transport.http_status,
                request_id=transport.request_id,
                response_sha256=transport.response_sha256,
                observation_sha256=observation.observation_sha256,
            ),
            observation=observation,
        )

    def inspect_account(self) -> PaperBrokerInspection:
        return self._inspect(1, ReadinessInspectionCode.ACCOUNT, _parse_account)

    def inspect_clock(self) -> PaperBrokerInspection:
        return self._inspect(2, ReadinessInspectionCode.CLOCK, _parse_clock)

    def inspect_instrument(self) -> PaperBrokerInspection:
        return self._inspect(3, ReadinessInspectionCode.INSTRUMENT, _parse_instrument)

    def inspect_positions(self) -> PaperBrokerInspection:
        return self._inspect(4, ReadinessInspectionCode.POSITIONS, _parse_inventory("POSITIONS"))

    def inspect_open_orders(self) -> PaperBrokerInspection:
        return self._inspect(
            5, ReadinessInspectionCode.OPEN_ORDERS, _parse_inventory("OPEN_ORDERS")
        )

    def inspect_latest_quote(self) -> PaperBrokerInspection:
        return self._inspect(6, ReadinessInspectionCode.LATEST_QUOTE, _parse_quote)


def build_alpaca_paper_read_only_adapter(
    settings: PaperCredentialSettings,
    *,
    connection_factory: ConnectionFactory = _default_connection_factory,
    clock: Clock = _system_utc_now,
) -> AlpacaPaperReadOnlyAdapter:
    """Run the complete credential gate before constructing any transport object."""

    credentials = settings.require_credentials()
    return AlpacaPaperReadOnlyAdapter(
        credentials,
        connection_factory=connection_factory,
        clock=clock,
    )


__all__ = [
    "HTTPS_TIMEOUT_SECONDS",
    "MAX_RESPONSE_BYTES",
    "AlpacaPaperReadOnlyAdapter",
    "ConnectionFactory",
    "build_alpaca_paper_read_only_adapter",
]
