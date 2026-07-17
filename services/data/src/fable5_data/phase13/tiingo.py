"""Fixed-target, header-authenticated Tiingo candidate reader for Phase 13 qualification."""

from __future__ import annotations

import http.client
import json
import ssl
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from fable5_data.phase13.adapters import (
    PointInTimeQualificationAdapter,
    build_capability_manifest,
    build_request_evidence,
)
from fable5_data.phase13.canonical import (
    PHASE13_FIXED_ENDPOINTS,
    PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN,
    PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN,
    PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN,
    PHASE13_TRANSPORT_PROFILE_SHA256,
    TIINGO_QUALIFICATION_HOST,
    TIINGO_QUALIFICATION_PORT,
    domain_sha256,
    raw_response_sha256,
)
from fable5_data.phase13.contracts import (
    QualificationCapability,
    QualificationCapabilityManifest,
    QualificationCheckStatus,
    QualificationProviderProfile,
    QualificationReasonCode,
    QualificationRequestCode,
    QualificationRequestEvidence,
    QualificationRequestStatus,
    QualificationSourceKind,
    QualificationUseRightsAttestation,
)
from fable5_data.phase13.settings import TiingoQualificationAccess, TiingoQualificationSettings

PHASE13_TIINGO_TIMEOUT_SECONDS = 10
PHASE13_TIINGO_MAX_RESPONSE_BYTES = 2_000_000
_MAX_ABSOLUTE_NUMBER = Decimal("1e18")
_MIN_DECIMAL_EXPONENT = -18


class _HTTPResponse(Protocol):
    status: int

    def read(self, amt: int | None = None) -> bytes: ...


class _HTTPSConnection(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
    ) -> None: ...

    def getresponse(self) -> _HTTPResponse: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[[], _HTTPSConnection]


@dataclass(frozen=True, slots=True)
class _ParsedSummary:
    record_count: int
    missingness_count: int
    revision_count: int
    event_time_min_utc: datetime
    event_time_max_utc: datetime
    available_at_min_utc: datetime
    available_at_max_utc: datetime
    schema_identity_sha256: str
    normalized_evidence_sha256: str


@dataclass(frozen=True, slots=True)
class _CapturedRequest:
    evidence: QualificationRequestEvidence
    summary: _ParsedSummary | None


class _CandidateFailure(RuntimeError):
    def __init__(self, reason: QualificationReasonCode) -> None:
        super().__init__("candidate qualification request failed")
        self.reason = reason


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _CandidateFailure(QualificationReasonCode.DUPLICATE_JSON_KEY)
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> object:
    raise _CandidateFailure(QualificationReasonCode.NON_FINITE_NUMBER)


def _parse_integer(value: str) -> int:
    if len(value.lstrip("-")) > 19:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    parsed = int(value)
    if abs(parsed) > _MAX_ABSOLUTE_NUMBER:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    return parsed


def _parse_decimal(value: str) -> Decimal:
    if len(value) > 64:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise _CandidateFailure(QualificationReasonCode.NON_FINITE_NUMBER)
    exponent = parsed.as_tuple().exponent
    if not isinstance(exponent, int):  # pragma: no cover - guarded by is_finite
        raise _CandidateFailure(QualificationReasonCode.NON_FINITE_NUMBER)
    if abs(parsed) > _MAX_ABSOLUTE_NUMBER or exponent < _MIN_DECIMAL_EXPONENT:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    return parsed


def _strict_json(payload: bytes) -> object:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _CandidateFailure(QualificationReasonCode.MALFORMED_UTF8) from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_parse_decimal,
            parse_int=_parse_integer,
            parse_constant=_reject_nonfinite,
        )
    except _CandidateFailure:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _CandidateFailure(QualificationReasonCode.MALFORMED_JSON) from exc


def _objects(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    if any(not isinstance(item, dict) for item in value):
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    return [item for item in value if isinstance(item, dict)]


def _exact_fields(item: Mapping[str, object], fields: set[str]) -> None:
    if set(item) != fields:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)


def _date_or_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
    rendered = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(rendered)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError as exc:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT) from exc
        return datetime.combine(parsed_date, time.min, tzinfo=UTC)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _conservative_date_availability(event: datetime) -> datetime:
    source_date = event.astimezone(UTC).date()
    eastern = ZoneInfo("America/New_York")
    return datetime.combine(source_date + timedelta(days=1), time.min, tzinfo=eastern).astimezone(
        UTC
    )


def _source_availability(value: object) -> datetime:
    event = _date_or_datetime(value)
    if isinstance(value, str) and len(value) == 10:
        return _conservative_date_availability(event)
    return event


def _require_aapl_identity(item: Mapping[str, object]) -> str:
    perma_ticker = item.get("permaTicker")
    if item.get("ticker") != "AAPL" or not isinstance(perma_ticker, str) or not perma_ticker:
        raise _CandidateFailure(QualificationReasonCode.IDENTITY_INVALID)
    return perma_ticker


def _summary(
    *,
    code: QualificationRequestCode,
    records: list[dict[str, object]],
    event_times: list[datetime],
    available_times: list[datetime],
    missingness_count: int,
    revision_count: int,
) -> _ParsedSummary:
    if not event_times or len(event_times) != len(available_times):
        raise _CandidateFailure(QualificationReasonCode.TEMPORAL_INVALID)
    schema_shape = tuple(sorted((key, type(value).__name__) for key, value in records[0].items()))
    schema_hash = domain_sha256(
        PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN,
        {"request_code": code, "shape": schema_shape},
    )
    normalized_hash = domain_sha256(
        PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN,
        {
            "request_code": code,
            "record_count": len(records),
            "missingness_count": missingness_count,
            "revision_count": revision_count,
            "event_times": tuple(event_times),
            "available_times": tuple(available_times),
            "schema_identity_sha256": schema_hash,
        },
    )
    return _ParsedSummary(
        record_count=len(records),
        missingness_count=missingness_count,
        revision_count=revision_count,
        event_time_min_utc=min(event_times),
        event_time_max_utc=max(event_times),
        available_at_min_utc=min(available_times),
        available_at_max_utc=max(available_times),
        schema_identity_sha256=schema_hash,
        normalized_evidence_sha256=normalized_hash,
    )


def _parse_meta(value: object) -> _ParsedSummary:
    records = _objects(value)
    fields = {
        "permaTicker",
        "ticker",
        "isActive",
        "statementLastUpdated",
        "dailyLastUpdated",
    }
    selected: list[dict[str, object]] = []
    missingness = 0
    events: list[datetime] = []
    available: list[datetime] = []
    for item in records:
        _exact_fields(item, fields)
        if item.get("ticker") != "AAPL":
            continue
        if not isinstance(item.get("permaTicker"), str) or not isinstance(
            item.get("isActive"), bool
        ):
            raise _CandidateFailure(QualificationReasonCode.IDENTITY_INVALID)
        timestamps = [item.get("statementLastUpdated"), item.get("dailyLastUpdated")]
        populated = [_date_or_datetime(entry) for entry in timestamps if entry is not None]
        missingness += sum(entry is None for entry in timestamps)
        if not populated:
            raise _CandidateFailure(QualificationReasonCode.TEMPORAL_INVALID)
        events.append(max(populated))
        available.append(
            max(_source_availability(entry) for entry in timestamps if entry is not None)
        )
        selected.append(item)
    if len(selected) != 1:
        raise _CandidateFailure(QualificationReasonCode.IDENTITY_INVALID)
    return _summary(
        code=QualificationRequestCode.FUNDAMENTALS_META,
        records=selected,
        event_times=events,
        available_times=available,
        missingness_count=missingness,
        revision_count=1,
    )


def _parse_prices(value: object) -> _ParsedSummary:
    records = _objects(value)
    fields = {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjOpen",
        "adjHigh",
        "adjLow",
        "adjClose",
        "adjVolume",
        "divCash",
        "splitFactor",
    }
    events: list[datetime] = []
    grains: set[datetime] = set()
    for item in records:
        _exact_fields(item, fields)
        event = _date_or_datetime(item.get("date"))
        numeric_fields = fields - {"date"}
        if any(
            isinstance(item.get(field), bool) or not isinstance(item.get(field), (int, Decimal))
            for field in numeric_fields
        ):
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        if event in grains:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        grains.add(event)
        events.append(event)
    return _summary(
        code=QualificationRequestCode.EOD_PRICES,
        records=records,
        event_times=events,
        available_times=[_conservative_date_availability(item) for item in events],
        missingness_count=0,
        revision_count=len(records),
    )


def _parse_distributions(value: object) -> _ParsedSummary:
    records = _objects(value)
    fields = {
        "permaTicker",
        "ticker",
        "exDate",
        "paymentDate",
        "recordDate",
        "declarationDate",
        "amount",
        "distributionType",
        "distributionFrequency",
    }
    events: list[datetime] = []
    available: list[datetime] = []
    missingness = 0
    grains: set[tuple[str, datetime, str]] = set()
    for item in records:
        _exact_fields(item, fields)
        perma_ticker = _require_aapl_identity(item)
        event = _date_or_datetime(item.get("exDate"))
        distribution_type = item.get("distributionType")
        amount = item.get("amount")
        if not isinstance(distribution_type, str) or not distribution_type:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        if isinstance(amount, bool) or not isinstance(amount, (int, Decimal)):
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        grain = (perma_ticker, event, distribution_type)
        if grain in grains:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        grains.add(grain)
        events.append(event)
        declaration = item.get("declarationDate")
        if declaration is None:
            missingness += 1
            available.append(_conservative_date_availability(events[-1]))
        else:
            available.append(_source_availability(declaration))
    return _summary(
        code=QualificationRequestCode.DISTRIBUTIONS,
        records=records,
        event_times=events,
        available_times=available,
        missingness_count=missingness,
        revision_count=len(records),
    )


def _parse_splits(value: object) -> _ParsedSummary:
    records = _objects(value)
    fields = {
        "permaTicker",
        "ticker",
        "exDate",
        "splitFrom",
        "splitTo",
        "splitFactor",
        "splitStatus",
    }
    events: list[datetime] = []
    grains: set[tuple[str, datetime]] = set()
    for item in records:
        _exact_fields(item, fields)
        perma_ticker = _require_aapl_identity(item)
        if item.get("splitStatus") not in {"a", "c"}:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        if any(
            isinstance(item.get(field), bool) or not isinstance(item.get(field), (int, Decimal))
            for field in ("splitFrom", "splitTo", "splitFactor")
        ):
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        event = _date_or_datetime(item.get("exDate"))
        grain = (perma_ticker, event)
        if grain in grains:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        grains.add(grain)
        events.append(event)
    return _summary(
        code=QualificationRequestCode.SPLITS,
        records=records,
        event_times=events,
        available_times=[_conservative_date_availability(item) for item in events],
        missingness_count=len(records),
        revision_count=len(records),
    )


def _parse_statements(value: object) -> _ParsedSummary:
    records = _objects(value)
    fields = {"date", "quarter", "year", "statementData"}
    events: list[datetime] = []
    available: list[datetime] = []
    grains: set[tuple[datetime, int, int]] = set()
    missingness = 0
    revision_count = 0
    for item in records:
        _exact_fields(item, fields)
        quarter = item.get("quarter")
        year = item.get("year")
        if type(quarter) is not int or type(year) is not int:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        assert isinstance(quarter, int)
        assert isinstance(year, int)
        if quarter not in {1, 2, 3, 4} or not 1900 <= year <= 2100:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        statements = item.get("statementData")
        if not isinstance(statements, dict) or set(statements) != {
            "balanceSheet",
            "incomeStatement",
            "cashFlow",
            "overview",
        }:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        for entries in statements.values():
            if not isinstance(entries, list):
                raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {"dataCode", "value"}:
                    raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
                if not isinstance(entry.get("dataCode"), str):
                    raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
                statement_value = entry.get("value")
                if statement_value is None:
                    missingness += 1
                elif isinstance(statement_value, bool) or not isinstance(
                    statement_value, (int, Decimal)
                ):
                    raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
            revision_count += len(entries)
        source_date = item.get("date")
        event = _date_or_datetime(source_date)
        grain = (event, quarter, year)
        if grain in grains:
            raise _CandidateFailure(QualificationReasonCode.SCHEMA_DRIFT)
        grains.add(grain)
        events.append(event)
        available.append(_source_availability(source_date))
    return _summary(
        code=QualificationRequestCode.FUNDAMENTAL_STATEMENTS,
        records=records,
        event_times=events,
        available_times=available,
        missingness_count=missingness,
        revision_count=revision_count,
    )


_PARSERS: dict[QualificationRequestCode, Callable[[object], _ParsedSummary]] = {
    QualificationRequestCode.FUNDAMENTALS_META: _parse_meta,
    QualificationRequestCode.EOD_PRICES: _parse_prices,
    QualificationRequestCode.DISTRIBUTIONS: _parse_distributions,
    QualificationRequestCode.SPLITS: _parse_splits,
    QualificationRequestCode.FUNDAMENTAL_STATEMENTS: _parse_statements,
}


def _default_connection_factory() -> _HTTPSConnection:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return http.client.HTTPSConnection(
        TIINGO_QUALIFICATION_HOST,
        TIINGO_QUALIFICATION_PORT,
        timeout=PHASE13_TIINGO_TIMEOUT_SECONDS,
        context=context,
    )


class TiingoCandidatePointInTimeQualificationAdapter(PointInTimeQualificationAdapter):
    """One bounded Tiingo candidate reader; unsupported capabilities remain explicit gaps."""

    __slots__ = ("_access", "_clock", "_connection_factory", "_profile")

    def __init__(
        self,
        *,
        access: TiingoQualificationAccess,
        connection_factory: ConnectionFactory,
        clock: Callable[[], datetime],
    ) -> None:
        self._access = access
        self._connection_factory = connection_factory
        self._clock = clock
        self._profile = QualificationProviderProfile(
            source_kind=QualificationSourceKind.TIINGO_CANDIDATE_READ_ONLY,
            provider_id="tiingo-candidate",
            adapter_id="phase13-tiingo-candidate-qualification-adapter",
            adapter_version="phase13-tiingo-candidate-qualification-adapter-v1",
            dataset_id="tiingo-eod-fundamentals-candidate",
            product_id="tiingo-candidate-qualification-products",
            synthetic=False,
        )

    def __repr__(self) -> str:
        return "TiingoCandidatePointInTimeQualificationAdapter(read_only=True)"

    @property
    def source_kind(self) -> QualificationSourceKind:
        return QualificationSourceKind.TIINGO_CANDIDATE_READ_ONLY

    @property
    def profile(self) -> QualificationProviderProfile:
        return self._profile

    @property
    def rights_attestation(self) -> QualificationUseRightsAttestation:
        return self._access.rights_attestation

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE13_TRANSPORT_PROFILE_SHA256

    def _capture_endpoint(self, endpoint: Mapping[str, object]) -> _CapturedRequest:
        ordinal_value = endpoint["ordinal"]
        if not isinstance(ordinal_value, int):  # pragma: no cover - frozen constant
            raise ValueError("fixed endpoint ordinal is invalid")
        ordinal = ordinal_value
        code = QualificationRequestCode(str(endpoint["code"]))
        target = str(endpoint["target"])
        started = self._clock().astimezone(UTC)
        connection: _HTTPSConnection | None = None
        http_status: int | None = None
        raw_hash: str | None = None
        body_size: int | None = None
        try:
            connection = self._connection_factory()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Token {self._access.api_token.get_secret_value()}",
                "User-Agent": "Fable5-Phase13-Qualification/1",
            }
            connection.request("GET", target, headers=headers)
            response = connection.getresponse()
            http_status = response.status
            if 300 <= http_status <= 399:
                raise _CandidateFailure(QualificationReasonCode.REDIRECT_REJECTED)
            if http_status != 200:
                raise _CandidateFailure(QualificationReasonCode.HTTP_FAILURE)
            raw = response.read(PHASE13_TIINGO_MAX_RESPONSE_BYTES + 1)
            if len(raw) > PHASE13_TIINGO_MAX_RESPONSE_BYTES:
                raise _CandidateFailure(QualificationReasonCode.RESPONSE_TOO_LARGE)
            raw_hash = raw_response_sha256(raw)
            body_size = len(raw)
            parsed = _strict_json(raw)
            summary = _PARSERS[code](parsed)
            completed = self._clock().astimezone(UTC)
            if summary.available_at_max_utc > completed:
                raise _CandidateFailure(QualificationReasonCode.TEMPORAL_INVALID)
            evidence = build_request_evidence(
                ordinal=ordinal,
                code=code,
                target=target,
                status=QualificationRequestStatus.OBSERVED,
                external_request_performed=True,
                request_started_at_utc=started,
                request_completed_at_utc=completed,
                reason_code=QualificationReasonCode.CHECK_PASSED,
                http_status=http_status,
                raw_body_sha256=raw_hash,
                body_size_bytes=body_size,
                record_count=summary.record_count,
            )
            return _CapturedRequest(evidence=evidence, summary=summary)
        except _CandidateFailure as exc:
            completed = self._clock().astimezone(UTC)
            evidence = build_request_evidence(
                ordinal=ordinal,
                code=code,
                target=target,
                status=QualificationRequestStatus.BLOCKED,
                external_request_performed=True,
                request_started_at_utc=started,
                request_completed_at_utc=completed,
                reason_code=exc.reason,
                http_status=http_status,
                raw_body_sha256=raw_hash,
                body_size_bytes=body_size,
            )
            return _CapturedRequest(evidence=evidence, summary=None)
        except Exception:
            completed = self._clock().astimezone(UTC)
            evidence = build_request_evidence(
                ordinal=ordinal,
                code=code,
                target=target,
                status=QualificationRequestStatus.BLOCKED,
                external_request_performed=True,
                request_started_at_utc=started,
                request_completed_at_utc=completed,
                reason_code=QualificationReasonCode.TRANSPORT_FAILURE,
            )
            return _CapturedRequest(evidence=evidence, summary=None)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _unsupported(
        self,
        capability: QualificationCapability,
        reason: QualificationReasonCode,
    ) -> QualificationCapabilityManifest:
        return build_capability_manifest(
            capability=capability,
            status=QualificationCheckStatus.UNCOMPUTABLE,
            reason_code=reason,
            decision_time_utc=self._clock().astimezone(UTC),
            event_time_min_utc=None,
            event_time_max_utc=None,
            available_at_min_utc=None,
            available_at_max_utc=None,
            record_count=0,
            missingness_count=1,
            revision_count=0,
            raw_evidence_sha256=None,
            normalized_evidence_sha256=None,
            schema_identity_sha256=None,
        )

    def inspect_capability(
        self, capability: QualificationCapability
    ) -> QualificationCapabilityManifest:
        if capability is QualificationCapability.POINT_IN_TIME_UNIVERSE_MEMBERSHIP:
            return self._unsupported(capability, QualificationReasonCode.CURRENT_UNIVERSE_ONLY)
        if capability is QualificationCapability.DELISTING_RETURN_SEMANTICS:
            return self._unsupported(
                capability, QualificationReasonCode.DELISTING_RETURN_UNAVAILABLE
            )
        endpoints = [
            item for item in PHASE13_FIXED_ENDPOINTS if item["capability"] == capability.value
        ]
        captures = tuple(self._capture_endpoint(item) for item in endpoints)
        blocked = next(
            (
                item.evidence.reason_code
                for item in captures
                if item.evidence.status is not QualificationRequestStatus.OBSERVED
            ),
            None,
        )
        summaries = tuple(item.summary for item in captures if item.summary is not None)
        decision_time = self._clock().astimezone(UTC)
        if blocked is not None or len(summaries) != len(captures):
            return build_capability_manifest(
                capability=capability,
                status=QualificationCheckStatus.BLOCKED,
                reason_code=blocked or QualificationReasonCode.TRANSPORT_FAILURE,
                decision_time_utc=decision_time,
                event_time_min_utc=None,
                event_time_max_utc=None,
                available_at_min_utc=None,
                available_at_max_utc=None,
                record_count=0,
                missingness_count=0,
                revision_count=0,
                raw_evidence_sha256=None,
                normalized_evidence_sha256=None,
                schema_identity_sha256=None,
                request_evidence=tuple(item.evidence for item in captures),
            )
        raw_hash = domain_sha256(
            PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN,
            tuple(item.evidence.raw_body_sha256 for item in captures),
        )
        normalized_hash = domain_sha256(
            PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN,
            tuple(item.normalized_evidence_sha256 for item in summaries),
        )
        schema_hash = domain_sha256(
            PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN,
            tuple(item.schema_identity_sha256 for item in summaries),
        )
        reason = QualificationReasonCode.CHECK_PASSED
        status = QualificationCheckStatus.PASS
        if capability is QualificationCapability.CORPORATE_ACTION_ANNOUNCEMENT_REVISION:
            reason = QualificationReasonCode.ACTION_REVISION_INVALID
            status = QualificationCheckStatus.BLOCKED
        elif capability is QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION:
            reason = QualificationReasonCode.FUNDAMENTAL_REVISION_INVALID
            status = QualificationCheckStatus.BLOCKED
        return build_capability_manifest(
            capability=capability,
            status=status,
            reason_code=reason,
            decision_time_utc=decision_time,
            event_time_min_utc=min(item.event_time_min_utc for item in summaries),
            event_time_max_utc=max(item.event_time_max_utc for item in summaries),
            available_at_min_utc=min(item.available_at_min_utc for item in summaries),
            available_at_max_utc=max(item.available_at_max_utc for item in summaries),
            record_count=sum(item.record_count for item in summaries),
            missingness_count=sum(item.missingness_count for item in summaries),
            revision_count=sum(item.revision_count for item in summaries),
            raw_evidence_sha256=raw_hash,
            normalized_evidence_sha256=normalized_hash,
            schema_identity_sha256=schema_hash,
            request_evidence=tuple(item.evidence for item in captures),
        )


def build_tiingo_candidate_qualification_adapter(
    settings: TiingoQualificationSettings,
    *,
    connection_factory: ConnectionFactory | None = None,
    clock: Callable[[], datetime] | None = None,
) -> TiingoCandidatePointInTimeQualificationAdapter:
    """Validate credential/rights input before constructing any transport-capable adapter."""

    selected_clock = clock or _system_utc_now
    access = settings.require_access(at_utc=selected_clock())
    selected_factory = connection_factory or _default_connection_factory
    return TiingoCandidatePointInTimeQualificationAdapter(
        access=access,
        connection_factory=selected_factory,
        clock=selected_clock,
    )


__all__ = [
    "PHASE13_TIINGO_MAX_RESPONSE_BYTES",
    "PHASE13_TIINGO_TIMEOUT_SECONDS",
    "ConnectionFactory",
    "TiingoCandidatePointInTimeQualificationAdapter",
    "build_tiingo_candidate_qualification_adapter",
]
