from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fable5_data.phase13.adapters import DeterministicMockPointInTimeQualificationAdapter
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
    QualificationCapability,
    QualificationReasonCode,
    QualificationUseRightsAttestation,
)
from fable5_data.phase13.settings import (
    PHASE13_TIINGO_ENV_NAMES,
    QualificationAccessUnavailable,
    TiingoQualificationAccess,
    TiingoQualificationSettings,
)
from fable5_data.phase13.tiingo import (
    PHASE13_TIINGO_MAX_RESPONSE_BYTES,
    TiingoCandidatePointInTimeQualificationAdapter,
    build_tiingo_candidate_qualification_adapter,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[3]


class _Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self, amt: int | None = None) -> bytes:
        return self.body if amt is None else self.body[:amt]


class _Connection:
    def __init__(self, body: bytes) -> None:
        self.response = _Response(body)

    def request(
        self,
        method: str,
        url: str,
        body: object | None = None,
        headers: object | None = None,
        *,
        encode_chunked: bool = False,
    ) -> None:
        del method, url, body, headers, encode_chunked

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        pass


def _rights() -> QualificationUseRightsAttestation:
    return QualificationUseRightsAttestation(
        attestation_id="phase13-security-rights-v1",
        attestation_sha256="2" * 64,
        valid_from_utc=datetime(2024, 1, 1, tzinfo=UTC),
        expires_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        storage_allowed=True,
        non_display_allowed=True,
        derived_data_allowed=True,
    )


def _candidate(body: bytes) -> TiingoCandidatePointInTimeQualificationAdapter:
    return TiingoCandidatePointInTimeQualificationAdapter(
        access=TiingoQualificationAccess(
            api_token=SecretStr("phase13-security-token-canary"),
            rights_attestation=_rights(),
        ),
        connection_factory=lambda: _Connection(body),
        clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
    )


def _clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in PHASE13_TIINGO_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_missing_or_partial_access_fails_before_transport_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_environment(monkeypatch)
    calls = 0

    def factory() -> _Connection:
        nonlocal calls
        calls += 1
        return _Connection(b"[]")

    with pytest.raises(QualificationAccessUnavailable):
        build_tiingo_candidate_qualification_adapter(
            TiingoQualificationSettings(),
            connection_factory=factory,
            clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
        )
    monkeypatch.setenv("FABLE5_TIINGO_RESEARCH_API_TOKEN", "partial-token-canary")
    with pytest.raises(QualificationAccessUnavailable):
        build_tiingo_candidate_qualification_adapter(
            TiingoQualificationSettings(),
            connection_factory=factory,
            clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
        )
    assert calls == 0


def test_secret_repr_and_sanitized_access_failure_never_render_canary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_environment(monkeypatch)
    canary = "phase13-unique-secret-canary"
    access = TiingoQualificationAccess(api_token=SecretStr(canary), rights_attestation=_rights())
    adapter = TiingoCandidatePointInTimeQualificationAdapter(
        access=access,
        connection_factory=lambda: _Connection(b"[]"),
        clock=lambda: datetime(2024, 6, 1, tzinfo=UTC),
    )
    assert canary not in repr(access)
    assert canary not in repr(adapter)
    with pytest.raises(QualificationAccessUnavailable) as captured:
        TiingoQualificationSettings().require_access(at_utc=datetime(2024, 6, 1, tzinfo=UTC))
    assert canary not in str(captured.value)


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"\xff", QualificationReasonCode.MALFORMED_UTF8),
        (
            b'[{"date":"2020-08-28","date":"2020-08-29"}]',
            QualificationReasonCode.DUPLICATE_JSON_KEY,
        ),
        (b"[NaN]", QualificationReasonCode.NON_FINITE_NUMBER),
        (b"[1000000000000000001]", QualificationReasonCode.SCHEMA_DRIFT),
        (b"not-json", QualificationReasonCode.MALFORMED_JSON),
        (
            b" " * (PHASE13_TIINGO_MAX_RESPONSE_BYTES + 1),
            QualificationReasonCode.RESPONSE_TOO_LARGE,
        ),
    ],
    ids=(
        "malformed-utf8",
        "duplicate-key",
        "nonfinite",
        "oversized-number",
        "malformed-json",
        "oversize-body",
    ),
)
def test_malformed_external_bodies_fail_closed_without_retention(
    body: bytes,
    reason: QualificationReasonCode,
) -> None:
    manifest = _candidate(body).inspect_capability(QualificationCapability.RAW_OHLCV_AVAILABILITY)
    assert manifest.reason_code is reason
    rendered = manifest.model_dump_json()
    assert "phase13-security-token-canary" not in rendered
    assert "not-json" not in rendered


class _MemoryStore:
    def __init__(self) -> None:
        self.artifact: PointInTimeQualificationArtifact | None = None

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_MemoryStore]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        if self.artifact is not None and self.artifact.qualification_idempotency_key == key:
            return self.artifact
        return None

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        self.artifact = artifact
        return artifact

    def get_qualification(self, qualification_id: object) -> PointInTimeQualificationArtifact:
        del qualification_id
        assert self.artifact is not None
        return self.artifact


def test_mock_workflow_passes_under_active_socket_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "socket", denied)
    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=_MemoryStore(),  # type: ignore[arg-type]
        phase13_code_version_git_sha="c" * 40,
    )
    artifact = workflow.create_qualification(
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key="phase13-network-denied-v1"
        )
    )
    assert len(artifact.capability_manifests) == 6
    assert len(artifact.checks) == 12


def test_production_sources_use_standard_library_without_generic_or_live_transport() -> None:
    phase13 = ROOT / "services/data/src/fable5_data/phase13"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in sorted(phase13.glob("*.py")))
    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "api.alpaca.markets",
        "paper-api.alpaca.markets",
        "submit_order",
        "place_order",
    ):
        assert forbidden not in sources
