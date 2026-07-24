from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fable5_paper.phase28.canonical import (
    PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    PHASE28_FIXED_ENDPOINTS,
)

from scripts import capture_alpaca_iex_observation_pilot as capture

ROOT = Path(__file__).resolve().parents[3]
GIT_SHA = "e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e"


def _clear_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABLE5_ALPACA_PAPER_API_KEY_ID", raising=False)
    monkeypatch.delenv("FABLE5_ALPACA_PAPER_SECRET_KEY", raising=False)


def test_mock_cli_needs_no_credentials_or_socket(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_credentials(monkeypatch)
    monkeypatch.setenv("FABLE5_CODE_VERSION_GIT_SHA", GIT_SHA)

    def blocked(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("network is forbidden")

    monkeypatch.setattr("http.client.HTTPSConnection", blocked)
    assert capture.main(["--deterministic-mock"]) == 0

    output = capsys.readouterr()
    artifact = json.loads(output.out)
    assert output.err == ""
    assert artifact["source_kind"] == "DETERMINISTIC_MOCK"
    assert all(
        inspection["external_request_performed"] is False for inspection in artifact["inspections"]
    )


def test_external_cli_requires_both_confirmations_before_credentials(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_credentials(monkeypatch)
    monkeypatch.setenv("FABLE5_CODE_VERSION_GIT_SHA", GIT_SHA)

    assert capture.main(["--confirm-credentialed-paper-only-external-observation"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == capture.FAILURE_MESSAGE + "\n"


def test_expired_review_stops_before_settings_or_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLE5_CODE_VERSION_GIT_SHA", GIT_SHA)
    arguments = capture._parser().parse_args(
        [
            "--confirm-credentialed-paper-only-external-observation",
            "--confirm-2026-07-24-exact-use-review",
        ]
    )

    def settings_forbidden() -> None:
        raise AssertionError("credential settings were constructed after expiry")

    monkeypatch.setattr(capture, "Phase28PaperCredentialSettings", settings_forbidden)
    with pytest.raises(capture.PilotInvocationError):
        capture._capture(
            arguments,
            clock=lambda: PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
        )


def test_missing_credentials_stop_before_socket(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_credentials(monkeypatch)
    monkeypatch.setenv("FABLE5_CODE_VERSION_GIT_SHA", GIT_SHA)

    def blocked(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("socket constructed before credential gate")

    monkeypatch.setattr("http.client.HTTPSConnection", blocked)
    monkeypatch.setattr(
        capture,
        "_system_utc_now",
        lambda: datetime(2026, 7, 24, 16, 0, tzinfo=UTC),
    )
    assert (
        capture.main(
            [
                "--confirm-credentialed-paper-only-external-observation",
                "--confirm-2026-07-24-exact-use-review",
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == capture.FAILURE_MESSAGE + "\n"


@pytest.mark.parametrize(
    "argument",
    [
        "--symbol",
        "--symbols",
        "--host",
        "--url",
        "--feed",
        "--currency",
        "--side",
        "--qty",
        "--price",
        "--strategy",
        "--retry",
    ],
)
def test_cli_rejects_dynamic_or_execution_shaped_arguments(argument: str) -> None:
    with pytest.raises(capture.PilotInvocationError):
        capture._parser().parse_args(["--deterministic-mock", argument, "canary"])


def test_production_phase28_has_no_loop_or_mutation_surface() -> None:
    production_files = sorted((ROOT / "services/paper/src/fable5_paper/phase28").glob("*.py"))
    production_files.append(ROOT / "scripts/capture_alpaca_iex_observation_pilot.py")
    forbidden_attributes = {
        "post",
        "put",
        "patch",
        "delete",
        "submit_order",
        "replace_order",
        "cancel_order",
        "liquidate",
        "close_position",
    }
    for path in production_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
        assert not any(isinstance(node, ast.AsyncFor) for node in ast.walk(tree))
        assert not {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }.intersection(forbidden_attributes)


def test_transport_manifest_is_six_fixed_gets_with_no_order_path() -> None:
    assert len(PHASE28_FIXED_ENDPOINTS) == 6
    assert all(item.method == "GET" and item.port == 443 for item in PHASE28_FIXED_ENDPOINTS)
    assert all("/orders" not in item.target for item in PHASE28_FIXED_ENDPOINTS)
    assert tuple(item.code for item in PHASE28_FIXED_ENDPOINTS) == (
        "ASSET_AAPL",
        "ASSET_MSFT",
        "ASSET_SPY",
        "LATEST_BARS",
        "LATEST_QUOTES",
        "SNAPSHOTS",
    )
