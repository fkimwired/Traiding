"""Fixed-origin Alpaca IEX GET-only adapter for Phase 28."""

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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from fable5_paper.phase12.settings import PaperCredentials
from fable5_paper.phase28.adapters import (
    ObservationInspection,
    TransientAsset,
    TransientBar,
    TransientBars,
    TransientQuote,
    TransientQuotes,
    TransientSnapshot,
    TransientSnapshots,
    build_inspection,
)
from fable5_paper.phase28.canonical import (
    PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    PHASE28_FIXED_ENDPOINTS,
    PHASE28_TRANSPORT_PROFILE_SHA256,
    PHASE28_UNIVERSE,
    domain_sha256,
    raw_response_sha256,
)
from fable5_paper.phase28.contracts import (
    InspectionCode,
    InspectionStatus,
    ObservationSourceKind,
)
from fable5_paper.phase28.settings import Phase28PaperCredentialSettings

MAX_RESPONSE_BYTES = 256 * 1024
HTTPS_TIMEOUT_SECONDS = 5.0
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _guard_provider_value(
    value: object, *, depth: int = 0, node_budget: list[int] | None = None
) -> None:
    budget = [20_000] if node_budget is None else node_budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 16:
        raise ValueError("response structure is too large")
    if isinstance(value, dict):
        if len(value) > 100:
            raise ValueError("response object is too large")
        for key, item in value.items():
            _guard_provider_value(key, depth=depth + 1, node_budget=budget)
            _guard_provider_value(item, depth=depth + 1, node_budget=budget)
    elif isinstance(value, (list, tuple)):
        if len(value) > 10_000:
            raise ValueError("response list is too large")
        for item in value:
            _guard_provider_value(item, depth=depth + 1, node_budget=budget)
    elif isinstance(value, str):
        if len(value) > 512 or _CONTROL_CHARACTERS.search(value):
            raise ValueError("response string is invalid")
    elif isinstance(value, Decimal):
        exponent = value.as_tuple().exponent
        if (
            not value.is_finite()
            or not isinstance(exponent, int)
            or len(value.as_tuple().digits) > 128
            or abs(exponent) > 1_000
            or (value != 0 and abs(value.adjusted()) > 1_000)
        ):
            raise ValueError("response number is outside bounds")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("provider timestamp must be timezone-aware")
    return value.astimezone(UTC)


class _StrictResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def values_are_bounded(self) -> _StrictResponse:
        _guard_provider_value(self.model_dump(mode="python"))
        return self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(sanitized=True)"

    def __str__(self) -> str:
        return self.__repr__()


class _AssetResponse(_StrictResponse):
    id: UUID
    asset_class: Literal["us_equity"] = Field(alias="class")
    exchange: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._:-]+$")
    symbol: str
    name: str | None = Field(default=None, max_length=256)
    status: str = Field(min_length=1, max_length=32, pattern=r"^[a-z_]+$")
    tradable: bool
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


class _Bar(_StrictResponse):
    timestamp: datetime = Field(alias="t")
    open_price: Decimal = Field(alias="o")
    high_price: Decimal = Field(alias="h")
    low_price: Decimal = Field(alias="l")
    close_price: Decimal = Field(alias="c")
    volume: Decimal = Field(alias="v")
    trade_count: Decimal | None = Field(default=None, alias="n")
    volume_weighted: Decimal | None = Field(default=None, alias="vw")

    _timestamp_is_utc = field_validator("timestamp")(_aware_utc)

    @model_validator(mode="after")
    def market_values_are_valid(self) -> _Bar:
        prices = (
            self.open_price,
            self.high_price,
            self.low_price,
            self.close_price,
        )
        if any(not value.is_finite() or value <= 0 for value in prices):
            raise ValueError("bar contains an invalid price")
        if not self.volume.is_finite() or self.volume < 0:
            raise ValueError("bar contains invalid volume")
        if self.trade_count is not None and (
            not self.trade_count.is_finite() or self.trade_count < 0
        ):
            raise ValueError("bar contains invalid trade count")
        if self.volume_weighted is not None and (
            not self.volume_weighted.is_finite() or self.volume_weighted <= 0
        ):
            raise ValueError("bar contains invalid volume-weighted price")
        if not (
            self.low_price
            <= min(self.open_price, self.close_price)
            <= max(self.open_price, self.close_price)
            <= self.high_price
        ):
            raise ValueError("bar price relationships are invalid")
        return self


class _Quote(_StrictResponse):
    timestamp: datetime = Field(alias="t")
    ask_price: Decimal = Field(alias="ap")
    bid_price: Decimal = Field(alias="bp")
    ask_size: Decimal | None = Field(default=None, alias="as")
    bid_size: Decimal | None = Field(default=None, alias="bs")
    ask_exchange: str | None = Field(default=None, alias="ax")
    bid_exchange: str | None = Field(default=None, alias="bx")
    conditions: list[str] | None = Field(default=None, alias="c")
    tape: str | None = Field(default=None, alias="z")

    _timestamp_is_utc = field_validator("timestamp")(_aware_utc)

    @model_validator(mode="after")
    def quote_values_are_valid(self) -> _Quote:
        if (
            not self.ask_price.is_finite()
            or not self.bid_price.is_finite()
            or self.ask_price <= 0
            or self.bid_price <= 0
            or self.ask_price < self.bid_price
        ):
            raise ValueError("quote prices are invalid")
        for size in (self.ask_size, self.bid_size):
            if size is not None and (not size.is_finite() or size < 0):
                raise ValueError("quote size is invalid")
        return self


class _Trade(_StrictResponse):
    timestamp: datetime = Field(alias="t")
    price: Decimal = Field(alias="p")
    size: Decimal = Field(alias="s")
    exchange: str | None = Field(default=None, alias="x")
    conditions: list[str] | None = Field(default=None, alias="c")
    trade_id: int | str | None = Field(default=None, alias="i")
    tape: str | None = Field(default=None, alias="z")

    _timestamp_is_utc = field_validator("timestamp")(_aware_utc)

    @model_validator(mode="after")
    def trade_values_are_valid(self) -> _Trade:
        if (
            not self.price.is_finite()
            or not self.size.is_finite()
            or self.price <= 0
            or self.size <= 0
        ):
            raise ValueError("trade values are invalid")
        return self


class _BarsResponse(_StrictResponse):
    bars: dict[str, _Bar]
    currency: Literal["USD"] | None = None


class _QuotesResponse(_StrictResponse):
    quotes: dict[str, _Quote]
    currency: Literal["USD"] | None = None


class _Snapshot(_StrictResponse):
    latest_trade: _Trade | None = Field(default=None, alias="latestTrade")
    latest_quote: _Quote | None = Field(default=None, alias="latestQuote")
    minute_bar: _Bar | None = Field(default=None, alias="minuteBar")
    daily_bar: _Bar | None = Field(default=None, alias="dailyBar")
    previous_daily_bar: _Bar | None = Field(default=None, alias="prevDailyBar")


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
    host: str, port: int, timeout: float, context: ssl.SSLContext
) -> _HttpsConnection:
    return cast(
        _HttpsConnection,
        http.client.HTTPSConnection(host=host, port=port, timeout=timeout, context=context),
    )


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("transport clock must be timezone-aware")
    return value.astimezone(UTC)


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
    if len(digits) > 128:
        raise ValueError("response number is too large")
    try:
        exponent = int(exponent_text or "0")
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("response number is invalid") from None
    if not parsed.is_finite() or abs(exponent) > 1_000:
        raise ValueError("response number is outside bounds")
    return parsed


def _decode_json(body: bytes) -> object:
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError("response BOM is forbidden")
    return json.loads(
        body.decode("utf-8", errors="strict"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_float=_bounded_decimal,
        parse_int=_bounded_decimal,
        parse_constant=_reject_constant,
    )


class _TransportFailure(RuntimeError):
    def __init__(
        self,
        reason: str,
        *,
        started_at_utc: datetime,
        completed_at_utc: datetime,
        http_status: int | None = None,
        request_id_sha256: str | None = None,
        response_sha256: str | None = None,
        external_request_performed: bool,
    ) -> None:
        super().__init__("Phase 28 transport was blocked")
        self.reason = reason
        self.started_at_utc = started_at_utc
        self.completed_at_utc = completed_at_utc
        self.http_status = http_status
        self.request_id_sha256 = request_id_sha256
        self.response_sha256 = response_sha256
        self.external_request_performed = external_request_performed


class ExactUseReviewUnavailable(RuntimeError):
    """The narrow current first-party review does not authorize an external request."""

    def __init__(self) -> None:
        super().__init__("Phase 28 exact-use review is unavailable")


def _require_current_exact_use_review() -> None:
    """Use the system clock, never a caller-supplied evidence clock, for authority."""

    if _normalize_utc(_system_utc_now()) >= PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC:
        raise ExactUseReviewUnavailable


class _TransportResponse:
    __slots__ = (
        "body",
        "completed_at_utc",
        "http_status",
        "request_id_sha256",
        "response_sha256",
        "started_at_utc",
    )

    def __init__(
        self,
        *,
        body: bytes,
        started_at_utc: datetime,
        completed_at_utc: datetime,
        request_id_sha256: str | None,
        response_sha256: str,
    ) -> None:
        self.body = body
        self.started_at_utc = started_at_utc
        self.completed_at_utc = completed_at_utc
        self.http_status = 200
        self.request_id_sha256 = request_id_sha256
        self.response_sha256 = response_sha256

    def __repr__(self) -> str:
        return "_TransportResponse(sanitized=True)"


class _FixedAlpacaIexTransport:
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

    def fetch(self, code: InspectionCode) -> _TransportResponse:
        if not isinstance(code, InspectionCode):
            raise TypeError("inspection code is outside the frozen registry")
        endpoint = PHASE28_FIXED_ENDPOINTS[tuple(InspectionCode).index(code)]
        started = _normalize_utc(self._clock())
        connection: _HttpsConnection | None = None
        response: _HttpsResponse | None = None
        request_performed = False
        try:
            context = ssl.create_default_context()
            if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
                raise ValueError("TLS verification is unavailable")
            _require_current_exact_use_review()
            connection = self._connection_factory(
                endpoint.host,
                endpoint.port,
                HTTPS_TIMEOUT_SECONDS,
                context,
            )
            _require_current_exact_use_review()
            connection.request(
                "GET",
                endpoint.target,
                body=None,
                headers={
                    "Accept": "application/json",
                    "APCA-API-KEY-ID": self._credentials.api_key_id.get_secret_value(),
                    "APCA-API-SECRET-KEY": self._credentials.secret_key.get_secret_value(),
                },
            )
            request_performed = True
            response = connection.getresponse()
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                declared = int(content_length)
                if declared < 0 or declared > MAX_RESPONSE_BYTES:
                    raise ValueError("response body is oversized")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError("response body is oversized")
            completed = _normalize_utc(self._clock())
            digest = raw_response_sha256(body)
            request_id = response.getheader("X-Request-ID")
            if request_id is not None and _REQUEST_ID.fullmatch(request_id) is None:
                raise ValueError("request identifier is invalid")
            request_id_sha256 = (
                domain_sha256("phase28-provider-request-id-v1", {"request_id": request_id})
                if request_id is not None
                else None
            )
            content_type = response.getheader("Content-Type")
            if content_type is None or content_type.split(";", 1)[0].strip().casefold() != (
                "application/json"
            ):
                raise _TransportFailure(
                    "response_content_type_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id_sha256=request_id_sha256,
                    response_sha256=digest,
                    external_request_performed=request_performed,
                )
            if 300 <= response.status <= 399:
                raise _TransportFailure(
                    "transport_redirect_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id_sha256=request_id_sha256,
                    response_sha256=digest,
                    external_request_performed=request_performed,
                )
            if response.status != 200:
                raise _TransportFailure(
                    "transport_http_status_blocked",
                    started_at_utc=started,
                    completed_at_utc=completed,
                    http_status=response.status,
                    request_id_sha256=request_id_sha256,
                    response_sha256=digest,
                    external_request_performed=request_performed,
                )
            return _TransportResponse(
                body=body,
                started_at_utc=started,
                completed_at_utc=completed,
                request_id_sha256=request_id_sha256,
                response_sha256=digest,
            )
        except ExactUseReviewUnavailable:
            completed = _normalize_utc(self._clock())
            raise _TransportFailure(
                "exact_use_review_unavailable",
                started_at_utc=started,
                completed_at_utc=completed,
                external_request_performed=False,
            ) from None
        except _TransportFailure:
            raise
        except Exception:
            completed = _normalize_utc(self._clock())
            raise _TransportFailure(
                "transport_unavailable",
                started_at_utc=started,
                completed_at_utc=completed,
                external_request_performed=request_performed,
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


Parser = Callable[[object], TransientAsset | TransientBars | TransientQuotes | TransientSnapshots]


def _bar(value: _Bar) -> TransientBar:
    return TransientBar(
        event_time_utc=value.timestamp,
        open_price=value.open_price,
        close_price=value.close_price,
    )


def _quote(value: _Quote) -> TransientQuote:
    return TransientQuote(
        event_time_utc=value.timestamp,
        bid_price=value.bid_price,
        ask_price=value.ask_price,
    )


def _asset_parser(symbol: str) -> Parser:
    def parse(decoded: object) -> TransientAsset:
        value = _AssetResponse.model_validate(decoded)
        if value.symbol != symbol:
            raise ValueError("asset symbol mismatch")
        return TransientAsset(
            symbol=symbol,
            status=value.status,
            active=value.status == "active",
            tradable=value.tradable,
        )

    return parse


def _exact_symbols(values: dict[str, object]) -> None:
    if tuple(sorted(values)) != tuple(sorted(PHASE28_UNIVERSE)):
        raise ValueError("response symbol registry mismatch")


def _bars_parser(decoded: object) -> TransientBars:
    value = _BarsResponse.model_validate(decoded)
    _exact_symbols(cast(dict[str, object], value.bars))
    return TransientBars({symbol: _bar(value.bars[symbol]) for symbol in PHASE28_UNIVERSE})


def _quotes_parser(decoded: object) -> TransientQuotes:
    value = _QuotesResponse.model_validate(decoded)
    _exact_symbols(cast(dict[str, object], value.quotes))
    return TransientQuotes({symbol: _quote(value.quotes[symbol]) for symbol in PHASE28_UNIVERSE})


def _snapshots_parser(decoded: object) -> TransientSnapshots:
    if not isinstance(decoded, dict):
        raise ValueError("snapshot response is not an object")
    value = {
        symbol: _Snapshot.model_validate(snapshot)
        for symbol, snapshot in cast(dict[str, object], decoded).items()
    }
    _exact_symbols(cast(dict[str, object], value))

    def transient(snapshot: _Snapshot) -> TransientSnapshot:
        return TransientSnapshot(
            latest_trade_time_utc=(
                snapshot.latest_trade.timestamp if snapshot.latest_trade is not None else None
            ),
            latest_quote=(
                _quote(snapshot.latest_quote) if snapshot.latest_quote is not None else None
            ),
            minute_bar=(_bar(snapshot.minute_bar) if snapshot.minute_bar is not None else None),
            daily_bar=(_bar(snapshot.daily_bar) if snapshot.daily_bar is not None else None),
            previous_daily_bar=(
                _bar(snapshot.previous_daily_bar)
                if snapshot.previous_daily_bar is not None
                else None
            ),
        )

    return TransientSnapshots({symbol: transient(value[symbol]) for symbol in PHASE28_UNIVERSE})


class AlpacaIexObservationOnlyAdapter:
    """Six fixed GET inspections and no generic or mutating public method."""

    def __init__(
        self,
        credentials: PaperCredentials,
        *,
        exact_use_review_confirmed: bool,
        connection_factory: ConnectionFactory = _default_connection_factory,
        clock: Clock = _system_utc_now,
    ) -> None:
        if exact_use_review_confirmed is not True:
            raise ExactUseReviewUnavailable
        _require_current_exact_use_review()
        self._transport = _FixedAlpacaIexTransport(
            credentials, connection_factory=connection_factory, clock=clock
        )

    @property
    def source_kind(self) -> ObservationSourceKind:
        return ObservationSourceKind.ALPACA_IEX_READ_ONLY

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE28_TRANSPORT_PROFILE_SHA256

    @property
    def exact_use_review_confirmed_for_external_run(self) -> bool:
        return True

    def _inspect(self, ordinal: int, code: InspectionCode, parser: Parser) -> ObservationInspection:
        try:
            response = self._transport.fetch(code)
        except _TransportFailure as exc:
            return build_inspection(
                ordinal=ordinal,
                code=code,
                status=InspectionStatus.BLOCKED,
                external_request_performed=exc.external_request_performed,
                started_at_utc=exc.started_at_utc,
                completed_at_utc=exc.completed_at_utc,
                payload=None,
                http_status=exc.http_status,
                request_id_sha256=exc.request_id_sha256,
                response_sha256=exc.response_sha256,
                failure_reason=exc.reason,
            )
        try:
            payload = parser(_decode_json(response.body))
        except (
            TypeError,
            ValueError,
            ValidationError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return build_inspection(
                ordinal=ordinal,
                code=code,
                status=InspectionStatus.BLOCKED,
                external_request_performed=True,
                started_at_utc=response.started_at_utc,
                completed_at_utc=response.completed_at_utc,
                payload=None,
                http_status=200,
                request_id_sha256=response.request_id_sha256,
                response_sha256=response.response_sha256,
                failure_reason="response_schema_blocked",
            )
        return build_inspection(
            ordinal=ordinal,
            code=code,
            status=InspectionStatus.OBSERVED,
            external_request_performed=True,
            started_at_utc=response.started_at_utc,
            completed_at_utc=response.completed_at_utc,
            payload=payload,
            http_status=200,
            request_id_sha256=response.request_id_sha256,
            response_sha256=response.response_sha256,
        )

    def inspect_asset_aapl(self) -> ObservationInspection:
        return self._inspect(1, InspectionCode.ASSET_AAPL, _asset_parser("AAPL"))

    def inspect_asset_msft(self) -> ObservationInspection:
        return self._inspect(2, InspectionCode.ASSET_MSFT, _asset_parser("MSFT"))

    def inspect_asset_spy(self) -> ObservationInspection:
        return self._inspect(3, InspectionCode.ASSET_SPY, _asset_parser("SPY"))

    def inspect_latest_bars(self) -> ObservationInspection:
        return self._inspect(4, InspectionCode.LATEST_BARS, _bars_parser)

    def inspect_latest_quotes(self) -> ObservationInspection:
        return self._inspect(5, InspectionCode.LATEST_QUOTES, _quotes_parser)

    def inspect_snapshots(self) -> ObservationInspection:
        return self._inspect(6, InspectionCode.SNAPSHOTS, _snapshots_parser)


def build_alpaca_iex_observation_only_adapter(
    settings: Phase28PaperCredentialSettings,
    *,
    exact_use_review_confirmed: bool,
    connection_factory: ConnectionFactory = _default_connection_factory,
    clock: Clock = _system_utc_now,
) -> AlpacaIexObservationOnlyAdapter:
    if exact_use_review_confirmed is not True:
        raise ExactUseReviewUnavailable
    _require_current_exact_use_review()
    credentials = settings.require_credentials()
    return AlpacaIexObservationOnlyAdapter(
        credentials,
        exact_use_review_confirmed=True,
        connection_factory=connection_factory,
        clock=clock,
    )


__all__ = [
    "HTTPS_TIMEOUT_SECONDS",
    "MAX_RESPONSE_BYTES",
    "AlpacaIexObservationOnlyAdapter",
    "ConnectionFactory",
    "ExactUseReviewUnavailable",
    "build_alpaca_iex_observation_only_adapter",
]
