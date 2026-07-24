from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e"
BASELINE_TREE = "380ee0c86874e0aca3d7e30e9ff6d76f36441284"
PHASE27_ARTIFACT = "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json"
T009_DOCUMENT = "docs/RIGHTS_EVIDENCE_REQUIREMENTS_FAMILY_A.md"
T007_DOCUMENT = "docs/PLAN_SEC_EDGAR_QUALIFICATION.md"

EXPECTED_PHASE28_ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "DEVELOPMENT.md",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_28_ALPACA_IEX_OBSERVATION_ONLY_CANDIDATE_SCREEN_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_28.md",
        "scripts/capture_alpaca_iex_observation_pilot.py",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_phase1.py",
        "services/paper/src/fable5_paper/phase28/__init__.py",
        "services/paper/src/fable5_paper/phase28/adapters.py",
        "services/paper/src/fable5_paper/phase28/alpaca.py",
        "services/paper/src/fable5_paper/phase28/canonical.py",
        "services/paper/src/fable5_paper/phase28/contracts.py",
        "services/paper/src/fable5_paper/phase28/settings.py",
        "services/paper/src/fable5_paper/phase28/workflow.py",
        "services/paper/tests/test_phase28_adapters.py",
        "services/paper/tests/test_phase28_contracts.py",
        "services/paper/tests/test_phase28_security.py",
        "services/paper/tests/test_phase28_workflow.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_static.py",
        "tests/test_phase14_static.py",
        "tests/test_phase15_static.py",
        "tests/test_phase16_static.py",
        "tests/test_phase17_static.py",
        "tests/test_phase18_static.py",
        "tests/test_phase19_static.py",
        "tests/test_phase20_static.py",
        "tests/test_phase21_static.py",
        "tests/test_phase22_static.py",
        "tests/test_phase23_static.py",
        "tests/test_phase24_static.py",
        "tests/test_phase25_static.py",
        "tests/test_phase27_static.py",
        "tests/test_phase28_static.py",
        "tests/test_repository_policy.py",
    }
)

FIXED_ENDPOINTS = (
    (
        "ASSET_AAPL",
        "GET",
        "paper-api.alpaca.markets",
        443,
        "/v2/assets/AAPL",
    ),
    (
        "ASSET_MSFT",
        "GET",
        "paper-api.alpaca.markets",
        443,
        "/v2/assets/MSFT",
    ),
    (
        "ASSET_SPY",
        "GET",
        "paper-api.alpaca.markets",
        443,
        "/v2/assets/SPY",
    ),
    (
        "LATEST_BARS",
        "GET",
        "data.alpaca.markets",
        443,
        "/v2/stocks/bars/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
    (
        "LATEST_QUOTES",
        "GET",
        "data.alpaca.markets",
        443,
        "/v2/stocks/quotes/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
    (
        "SNAPSHOTS",
        "GET",
        "data.alpaca.markets",
        443,
        "/v2/stocks/snapshots?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase1_phase28_static", ROOT / "scripts/verify_phase1.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def changed_since_anchor() -> set[str]:
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    return changed


def test_phase28_baseline_parser_and_exact_ownership_are_closed() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_28_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_28_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_28_ALLOWED_WRITES == EXPECTED_PHASE28_ALLOWED_WRITES
    assert len(verifier.PHASE_28_ALLOWED_WRITES) == 44
    assert (
        verifier.phase28_path_manifest_sha256(verifier.PHASE_28_ALLOWED_WRITES)
        == verifier.PHASE_28_PATH_MANIFEST_SHA256
    )
    assert [verifier.phase_number(str(value)) for value in range(1, 29)] == list(range(1, 29))
    for invalid in ("0", "29", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)
    identity = subprocess.run(
        ["git", "show", "-s", "--format=%T", BASELINE_SHA],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert identity == BASELINE_TREE
    changed = changed_since_anchor()
    assert changed == EXPECTED_PHASE28_ALLOWED_WRITES
    assert verifier.phase28_ownership_delta(changed) == (set(), set())


def test_phase28_exact_content_manifest_is_closed_and_detects_drift() -> None:
    verifier = verifier_module()
    expected_content_paths = EXPECTED_PHASE28_ALLOWED_WRITES - {"scripts/verify_phase1.py"}
    assert verifier.PHASE_28_CONTENT_PATHS == expected_content_paths
    assert set(verifier.PHASE_28_FILE_SHA256) == expected_content_paths
    assert (
        verifier.phase28_content_manifest_sha256(verifier.PHASE_28_FILE_SHA256)
        == verifier.PHASE_28_CONTENT_MANIFEST_SHA256
    )
    actual = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in expected_content_paths
    }
    assert verifier.phase28_content_findings(actual) == (set(), set(), set())
    assert (
        verifier.phase28_content_manifest_sha256(actual)
        == verifier.PHASE_28_CONTENT_MANIFEST_SHA256
    )

    planted = dict(actual)
    planted["services/paper/src/fable5_paper/phase28/workflow.py"] = "0" * 64
    assert verifier.phase28_content_findings(planted) == (
        set(),
        set(),
        {"services/paper/src/fable5_paper/phase28/workflow.py"},
    )


def test_phase28_ownership_rejects_missing_extra_live_and_execution_paths() -> None:
    verifier = verifier_module()
    removed = "scripts/capture_alpaca_iex_observation_pilot.py"
    assert verifier.phase28_ownership_delta(set(EXPECTED_PHASE28_ALLOWED_WRITES) - {removed}) == (
        {removed},
        set(),
    )
    for planted in (
        "services/api/v1/phase28.py",
        "services/frontend/src/app/paper/phase28/page.tsx",
        "services/paper/src/fable5_paper/phase28/order_submit.py",
        "services/data/src/fable5_data/phase28/acquisition.py",
        "services/api/migrations/versions/0012_phase28.py",
    ):
        assert verifier.phase28_ownership_delta(
            set(EXPECTED_PHASE28_ALLOWED_WRITES) | {planted}
        ) == (set(), {planted})


def test_phase28_preserves_accepted_phase27_t009_t007_and_t010_bytes() -> None:
    verifier = verifier_module()
    assert len(verifier.PHASE_27_ALLOWED_WRITES) == 47
    for path in (
        PHASE27_ARTIFACT,
        T009_DOCUMENT,
        T007_DOCUMENT,
        "CLAUDE.md",
        "tests/test_status_currency.py",
    ):
        assert (ROOT / path).read_bytes() == git_blob(BASELINE_SHA, path)
    assert hashlib.sha256((ROOT / PHASE27_ARTIFACT).read_bytes()).hexdigest() == (
        "b2525ad22c1a0f1569188a7aefa3d735da1903d098725a8346c762d7c0d4214b"
    )
    assert hashlib.sha256((ROOT / T009_DOCUMENT).read_bytes()).hexdigest() == (
        "870227c6dd0fdeb0d8e38108db9eff841c4089fed241e289816c2ec5549bf7e8"
    )
    assert hashlib.sha256((ROOT / T007_DOCUMENT).read_bytes()).hexdigest() == (
        "255bd1777085416d13017d5cd16ff67ca453314930c7cd0e028c10c6b41bee91"
    )
    assert hashlib.sha256((ROOT / "CLAUDE.md").read_bytes()).hexdigest() == (
        "f6b8a657be1596f2547ea9d6711a36bafd171243f8f194476a7acdb4557ca9f2"
    )
    assert hashlib.sha256((ROOT / "tests/test_status_currency.py").read_bytes()).hexdigest() == (
        "5ed0f5efc8e112623a716a5f2631b8b2c36de374894198c1065b1ec277b4e958"
    )


def test_phase28_fixed_request_and_predicate_registries_are_exact() -> None:
    from fable5_paper.phase28 import canonical
    from fable5_paper.phase28.contracts import (
        InspectionCode,
        ObservationOutcome,
        PredicateCode,
    )

    assert canonical.PHASE28_UNIVERSE == ("AAPL", "MSFT", "SPY")
    assert canonical.PHASE28_FEED == "iex"
    assert canonical.PHASE28_CURRENCY == "USD"
    assert canonical.PHASE28_FRESHNESS_TTL_SECONDS == 120
    assert canonical.PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS == 60
    assert canonical.PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS == 30
    assert canonical.PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC == datetime(
        2026, 8, 1, 0, 0, tzinfo=UTC
    )
    assert canonical.PHASE28_EXACT_USE_REVIEW_SHA256 == (
        "d41e5d822918d5eaee04331d06c8dc5c567c1537363313a791573bfee7ad7725"
    )
    assert canonical.PHASE28_CONFIG_SHA256 == (
        "23c2059c06938c47e615539a4d4584770007ed7722796f0f38488020e449b514"
    )
    assert canonical.PHASE28_UNIVERSE_SHA256 == (
        "9c3f395b31a29e37b1937128d12b451ffc3e7c78360139046d4ee327cb0e0add"
    )
    assert canonical.PHASE28_SIGNAL_REGISTRY_SHA256 == (
        "b2327239149834cee7526ba983c5f4fe329ec08b0ef40eea5ebe3823d2cadc7b"
    )
    assert canonical.PHASE28_TRANSPORT_PROFILE_SHA256 == (
        "7bbabcd4965ff65ea26c9c56a2f19ede8e20342bedfaf26e020044316664a51d"
    )
    assert canonical.PHASE28_EXACT_USE_REVIEW_SOURCE_URLS == (
        "https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf",
        "https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf",
        "https://alpaca.markets/support/redistribute-alpaca-api",
        "https://docs.alpaca.markets/us/docs/market-data-faq",
    )
    assert (
        tuple(
            (
                endpoint.code,
                endpoint.method,
                endpoint.host,
                endpoint.port,
                endpoint.target,
            )
            for endpoint in canonical.PHASE28_FIXED_ENDPOINTS
        )
        == FIXED_ENDPOINTS
    )
    assert tuple(InspectionCode) == tuple(row[0] for row in FIXED_ENDPOINTS)
    assert tuple(ObservationOutcome) == ("MATCH", "NO_MATCH", "INSUFFICIENT_DATA")
    assert tuple(PredicateCode) == (
        "ASSET_ACTIVE",
        "ASSET_TRADABLE",
        "LATEST_BAR_VALID_AND_FRESH",
        "LATEST_QUOTE_VALID_AND_FRESH",
        "SNAPSHOT_COMPLETE_AND_FRESH",
        "CROSS_ENDPOINT_COHERENT",
        "SESSION_DIRECTION_POSITIVE",
        "INTRADAY_DIRECTION_POSITIVE",
    )
    assert "trade, quote, minute, daily, and prior daily bar" in (
        canonical.PHASE28_SIGNAL_DEFINITIONS[4].definition
    )
    assert canonical.PHASE28_SIGNAL_DEFINITIONS[5].definition == (
        "bar-to-minute-bar agrees within 60 seconds and quote-to-quote within 30 seconds"
    )
    assert "partial-market feed" in canonical.PHASE28_NOTICE
    assert "paper-only testing" in canonical.PHASE28_NOTICE
    assert "not research-qualified" in canonical.PHASE28_NOTICE
    assert "a trade signal" in canonical.PHASE28_NOTICE
    assert "investment advice" in canonical.PHASE28_NOTICE


def test_phase28_production_surface_is_cli_only_get_only_and_dependency_free() -> None:
    verifier = verifier_module()
    production_paths = (
        *sorted((ROOT / "services/paper/src/fable5_paper/phase28").glob("*.py")),
        ROOT / "scripts/capture_alpaca_iex_observation_pilot.py",
    )
    sources = {path.relative_to(ROOT).as_posix(): normalized(path) for path in production_paths}
    assert verifier.phase28_forbidden_surface_findings(sources) == set()
    assert all(
        not any(isinstance(node, ast.While) for node in ast.walk(ast.parse(source)))
        for source in sources.values()
    )

    transport = normalized(ROOT / "services/paper/src/fable5_paper/phase28/alpaca.py")
    assert transport.count('connection.request(\n                "GET",') == 1
    assert "http.client.HTTPSConnection" in transport
    assert "ssl.create_default_context()" in transport
    assert "context.check_hostname" in transport
    assert "ssl.CERT_REQUIRED" in transport
    assert "body=None" in transport
    assert "review_clock" not in transport
    transport_tree = ast.parse(transport)
    parent_by_node = {
        child: parent
        for parent in ast.walk(transport_tree)
        for child in ast.iter_child_nodes(parent)
    }
    request_calls = [
        node
        for node in ast.walk(transport_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "connection"
        and node.func.attr == "request"
    ]
    assert len(request_calls) == 1
    loop_types = (
        ast.For,
        ast.While,
        ast.AsyncFor,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    ancestor = parent_by_node.get(request_calls[0])
    while ancestor is not None:
        assert not isinstance(ancestor, loop_types)
        ancestor = parent_by_node.get(ancestor)
    review_guard_calls = [
        node
        for node in ast.walk(transport_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_require_current_exact_use_review"
    ]
    assert len(review_guard_calls) == 4
    fetch_source = transport.split(
        "    def fetch(self, code: InspectionCode) -> _TransportResponse:", 1
    )[1].split("\n\nclass AlpacaIexObservationOnlyAdapter:", 1)[0]
    first_review_guard = fetch_source.index("_require_current_exact_use_review()")
    connection_construction = fetch_source.index("connection = self._connection_factory(")
    second_review_guard = fetch_source.index(
        "_require_current_exact_use_review()", first_review_guard + 1
    )
    request_start = fetch_source.index("connection.request(")
    assert first_review_guard < connection_construction < second_review_guard < request_start
    constructor_source = transport.split("class AlpacaIexObservationOnlyAdapter:", 1)[1].split(
        "def build_alpaca_iex_observation_only_adapter(",
        1,
    )[0]
    builder_source = transport.split(
        "def build_alpaca_iex_observation_only_adapter(",
        1,
    )[1].split("\n\n__all__", 1)[0]
    assert constructor_source.count("_require_current_exact_use_review()") == 1
    assert builder_source.count("_require_current_exact_use_review()") == 1
    assert "hide_input_in_errors=True" in transport
    assert transport.count("(sanitized=True)") >= 2
    assert "def __repr__(self) -> str:" in transport
    assert "def __str__(self) -> str:" in transport
    for forbidden in (
        "allow_redirects",
        "max_redirects",
        "HTTPConnection(",
        "requests.",
        "httpx.",
        "aiohttp.",
        "alpaca-py",
        "alpaca_trade_api",
        "websocket",
        "setInterval",
    ):
        assert forbidden not in transport

    contracts = normalized(ROOT / "services/paper/src/fable5_paper/phase28/contracts.py")
    for required_contract_guard in (
        "self.request_started_at_utc >= PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC",
        "non-observed inspection cannot carry an observation hash",
        "blocked_seen = False",
        "external fail-closed ordering changed",
        "external inspection was unattempted before a block",
        "predicate classification lacks an observed dependency",
    ):
        assert required_contract_guard in contracts

    cli = normalized(ROOT / "scripts/capture_alpaca_iex_observation_pilot.py")
    assert cli.count('"--deterministic-mock"') == 1
    assert cli.count('"--confirm-credentialed-paper-only-external-observation"') == 1
    assert cli.count('"--confirm-2026-07-24-exact-use-review"') == 1
    for configurable_surface in (
        '"--symbol"',
        '"--symbols"',
        '"--host"',
        '"--url"',
        '"--path"',
        '"--feed"',
        '"--currency"',
        '"--timeframe"',
        '"--retry"',
        '"--account"',
        '"--side"',
        '"--qty"',
        '"--price"',
    ):
        assert configurable_surface not in cli

    workflow = normalized(ROOT / "services/paper/src/fable5_paper/phase28/workflow.py")
    coherence = workflow.split("bar_gap = abs(", 1)[1].split("session_positive: bool | None", 1)[0]
    assert "_utc(bar.event_time_utc)" in coherence
    assert "_utc(snapshot.minute_bar.event_time_utc)" in coherence
    assert "_utc(quote.event_time_utc)" in coherence
    assert "_utc(snapshot.latest_quote.event_time_utc)" in coherence
    assert "PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS" in coherence
    assert "PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS" in coherence
    assert "bar.event_time_utc) - _utc(quote.event_time_utc" not in coherence

    assert (ROOT / "packages/contracts/openapi.json").read_bytes() == git_blob(
        BASELINE_SHA, "packages/contracts/openapi.json"
    )
    assert (ROOT / "pyproject.toml").read_bytes() == git_blob(BASELINE_SHA, "pyproject.toml")
    assert not any(
        path.startswith(
            (
                "services/api/",
                "services/frontend/",
                "services/data/",
                "packages/contracts/",
            )
        )
        for path in changed_since_anchor()
    )


def test_phase28_evidence_contract_contains_no_raw_market_or_order_fields() -> None:
    from fable5_paper.phase28.contracts import (
        AlpacaIexObservationEvidence,
        ObservationAuthority,
        ObservationInspectionEvidence,
    )

    evidence_fields = set(AlpacaIexObservationEvidence.model_fields)
    inspection_fields = set(ObservationInspectionEvidence.model_fields)
    authority_fields = set(ObservationAuthority.model_fields)
    assert authority_fields == {
        "provider_payload_persisted",
        "raw_price_persisted",
        "research_qualified",
        "strategy_execution_eligible",
        "order_submission_authorized",
        "live_path_absent",
        "simulated_paper_only",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    }
    assert {
        "evidence_id",
        "evidence_sha256",
        "config_sha256",
        "universe_sha256",
        "signal_registry_sha256",
        "transport_profile_sha256",
        "code_version_git_sha",
        "random_seed",
        "trial_count",
        "forecast_horizon",
        "observation_snapshot_id",
        "observation_snapshot_sha256",
        "observation_snapshot_kind",
        "exact_use_review_sha256",
        "exact_use_review_revalidation_deadline_utc",
        "observed_at_utc",
        "authority",
        "notice",
    } <= evidence_fields
    forbidden = {
        "price",
        "open",
        "high",
        "low",
        "close",
        "bid",
        "ask",
        "size",
        "volume",
        "body",
        "headers",
        "credential",
        "secret",
        "token",
        "account",
        "position",
        "order",
        "side",
        "quantity",
    }
    assert not (evidence_fields & forbidden)
    assert "request_id" not in inspection_fields
    assert "request_id_sha256" in inspection_fields
    assert not (
        inspection_fields
        & {
            "body",
            "headers",
            "credential",
            "secret",
            "token",
            "raw_price",
            "raw_timestamp",
            "account",
            "position",
            "order",
        }
    )


def test_phase28_ci_is_additive_credential_free_and_never_runs_external_mode() -> None:
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-27-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "27"' in workflow
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 27") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 27") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 28") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 28") == 1
    assert "phase28-static:" in workflow
    assert "phase28-compose:" in workflow
    assert 'FABLE5_VERIFY_PHASE: "28"' in workflow
    assert "secrets." not in workflow
    for credential_name in (
        "FABLE5_ALPACA_PAPER_API_KEY_ID",
        "FABLE5_ALPACA_PAPER_SECRET_KEY",
    ):
        assert f'{credential_name}: ""' in workflow
    assert "--confirm-credentialed-paper-only-external-observation" not in workflow
    assert "capture_alpaca_iex_observation_pilot.py" not in workflow
    assert "curl " not in workflow
    assert "Invoke-RestMethod" not in workflow


def test_phase28_verifier_dispatches_static_and_inherited_compose_without_phase29() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "def verify_phase28_static()",
        "verify_phase28_static()",
        'print("Static repository policy checks passed for Phase 28.")',
        'print("Full Compose Phase 28 inherited verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "27")',
    ):
        assert required in verifier
    assert (ROOT / "docs/handoffs/PHASE_28.md").is_file()
    assert (ROOT / "services/paper/src/fable5_paper/phase28").is_dir()
    assert not (ROOT / "docs/handoffs/PHASE_29.md").exists()
    assert not (ROOT / "services/paper/src/fable5_paper/phase29").exists()
