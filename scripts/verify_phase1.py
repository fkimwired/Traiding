from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier

ROOT = Path(__file__).resolve().parents[1]
GATE_START = "1. **No live trading. Paper trading only.**"
GATE_END = "   are configured; never invent real results."
GATE_SHA256 = "1c6586b54c77c5a9df8e9838638631127cb2e5bc0af1c813b27b7f6af355d672"
REQUIRED_PATHS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "compose.yaml",
    "pyproject.toml",
    "requirements.lock",
    "package.json",
    "docs/PRODUCT_BRIEF.md",
    "docs/STRATEGY_CANON.md",
    "docs/EVALS.md",
    "docs/RISK_POLICY.md",
    "docs/DATA_SOURCES.md",
    "docs/COMPLIANCE_NOTES.md",
    "docs/RESEARCH_SUPPLEMENT.md",
    "packages/contracts/openapi.json",
    "packages/contracts/src/api.generated.ts",
    "services/api/Dockerfile",
    "services/api/migrations/versions/0001_phase1_audit_spine.py",
    "services/api/src/fable5_api/main.py",
    "services/jobs/Dockerfile",
    "services/jobs/src/fable5_jobs/worker.py",
    "services/frontend/Dockerfile",
    "services/frontend/src/app/page.tsx",
    "services/backtester/README.md",
    "services/extraction/README.md",
    "services/risk/README.md",
    "strategy_specs/README.md",
)
PHASE_2_REQUIRED_PATHS = (
    "docs/PHASE_02_SCHEMA_DECISIONS.md",
    "docs/QWEN_REVIEW_PHASE_02.md",
    "docs/handoffs/PHASE_03.md",
    "services/api/migrations/versions/0002_phase2_source_extraction.py",
    "services/api/src/fable5_api/idea_intake.py",
    "services/extraction/src/fable5_extraction/models.py",
    "services/extraction/src/fable5_extraction/extractor.py",
    "services/extraction/src/fable5_extraction/memo.py",
    "services/extraction/src/fable5_extraction/repository.py",
    "services/extraction/src/fable5_extraction/workflow.py",
    "services/jobs/src/fable5_jobs/extraction.py",
)
PHASE_2_FIXTURES = (
    "ranking.json",
    "trend.json",
    "social_news.json",
    "pairs.json",
    "order_flow.json",
    "unusual_options.json",
)
PHASE_2_TABLES = (
    "research_sources",
    "research_source_versions",
    "research_source_version_corroborations",
    "extraction_requests",
    "extraction_events",
    "trading_idea_cards",
    "card_official_corroborations",
    "research_memos",
)
PHASE_2_APPEND_ONLY_ERROR = "Phase 2 research records are append-only"
PHASE_3_REQUIRED_PATHS = (
    "docs/PHASE_03_MAPPING_DECISIONS.md",
    "docs/QWEN_REVIEW_PHASE_03.md",
    "docs/handoffs/PHASE_04.md",
    "services/api/migrations/versions/0003_phase3_canon_mapping.py",
    "services/api/src/fable5_api/mappings.py",
    "services/mapping/src/fable5_mapping/models.py",
    "services/mapping/src/fable5_mapping/rules.py",
    "services/mapping/src/fable5_mapping/mapper.py",
    "services/mapping/src/fable5_mapping/rationale.py",
    "services/mapping/src/fable5_mapping/repository.py",
    "services/mapping/src/fable5_mapping/workflow.py",
    "services/mapping/tests",
    "services/frontend/src/app/ideas/IdeaMappings.tsx",
)
PHASE_3_TABLES = (
    "research_mapping_versions",
    "mapping_official_corroborations",
    "mapping_rationale_artifacts",
)
PHASE_3_APPEND_ONLY_ERROR = "Phase 3 mapping records are append-only"
PHASE_3_CANONICAL_FAMILIES = {
    "A_CROSS_SECTIONAL_EQUITY_RANKING",
    "B_TIME_SERIES_MOMENTUM_REGIME",
    "C_OFFICIAL_EVENT_TEXT_OVERLAY",
    "D_PAIRS_STATISTICAL_ARBITRAGE",
    "E_ORDER_BOOK_MICROSTRUCTURE",
    "F_OPTIONS_FLOW_IV_RV_ANALYTICS",
}
PHASE_3_VERDICTS = {
    "BUILD_RESEARCH",
    "DEFER",
    "DEFER_READ_ONLY",
    "REJECT_PLATFORM",
    "NON_TESTABLE",
}
PHASE_3_REQUIRED_REASONS = {
    "missing_raw_text",
    "missing_action_rule",
    "ambiguous_action_rule",
    "missing_forecast_horizon",
    "ambiguous_forecast_horizon",
    "MISSING_CANONICAL_FAMILY",
    "AMBIGUOUS_CANONICAL_FAMILY",
    "PLATFORM_INFRASTRUCTURE_MISMATCH",
    "OFFICIAL_CORROBORATION_REQUIRED",
    "BORROW_AND_BREAK_REQUIREMENTS",
    "READ_ONLY_ANALYTICS_ONLY",
}
PHASE_3_RULE_SET_SHA256 = "352afeee889857834f7453f2d37bbb6b40e414ac4da9befccce476cc2061674a"
PHASE_3_FIXTURE_MATRIX: dict[str, tuple[str, str, list[str] | None]] = {
    "ranking.json": ("A_CROSS_SECTIONAL_EQUITY_RANKING", "BUILD_RESEARCH", None),
    "trend.json": (
        "B_TIME_SERIES_MOMENTUM_REGIME",
        "NON_TESTABLE",
        ["missing_forecast_horizon"],
    ),
    "social_news.json": (
        "C_OFFICIAL_EVENT_TEXT_OVERLAY",
        "DEFER",
        ["OFFICIAL_CORROBORATION_REQUIRED"],
    ),
    "pairs.json": (
        "D_PAIRS_STATISTICAL_ARBITRAGE",
        "DEFER",
        ["BORROW_AND_BREAK_REQUIREMENTS"],
    ),
    "order_flow.json": (
        "E_ORDER_BOOK_MICROSTRUCTURE",
        "REJECT_PLATFORM",
        ["PLATFORM_INFRASTRUCTURE_MISMATCH"],
    ),
    "unusual_options.json": (
        "F_OPTIONS_FLOW_IV_RV_ANALYTICS",
        "NON_TESTABLE",
        ["missing_action_rule"],
    ),
}
PHASE_4_REQUIRED_PATHS = (
    "docs/PHASE_04_DATA_DECISIONS.md",
    "services/api/migrations/versions/0004_phase4_point_in_time_data.py",
    "services/api/src/fable5_api/data_snapshots.py",
    "services/api/tests/test_phase4_routes.py",
    "services/data/src/fable5_data/__init__.py",
    "services/data/src/fable5_data/adapters.py",
    "services/data/src/fable5_data/canonical.py",
    "services/data/src/fable5_data/contracts.py",
    "services/data/src/fable5_data/quality.py",
    "services/data/src/fable5_data/repository.py",
    "services/data/src/fable5_data/snapshots.py",
    "services/data/src/fable5_data/synthetic.py",
    "services/data/src/fable5_data/workflow.py",
    "services/data/src/fable5_data/fixtures/phase4_synthetic_pit_v1.json",
    "services/data/tests/test_adapters.py",
    "services/data/tests/test_canonical.py",
    "services/data/tests/test_contracts.py",
    "services/data/tests/test_phase4_repository.py",
    "services/data/tests/test_phase4_workflow.py",
    "services/data/tests/test_quality.py",
    "services/data/tests/test_snapshots.py",
    "tests/test_phase4_migration.py",
    "tests/test_phase4_postgres.py",
)
PHASE_4_TABLES = (
    "data_snapshots",
    "data_raw_observations",
    "data_observation_revisions",
    "data_normalized_observations",
    "data_snapshot_constituents",
    "data_quality_findings",
    "data_snapshot_manifests",
)
PHASE_5_REQUIRED_PATHS = (
    "services/api/migrations/versions/0005_phase5_evaluation.py",
    "services/api/src/fable5_api/evaluations.py",
    "services/api/tests/test_phase5_routes.py",
    "services/api/tests/test_phase5_openapi_contract.py",
    "services/backtester/src/fable5_backtester/__init__.py",
    "services/backtester/src/fable5_backtester/outcomes.py",
    "services/backtester/src/fable5_backtester/source_lineage.py",
    "services/backtester/tests",
    "services/frontend/src/app/research/EvaluationReports.tsx",
    "services/frontend/src/tests/EvaluationReports.test.tsx",
    "packages/contracts/src/phase5-contract.type-test.ts",
    "tests/test_phase5_migration.py",
    "tests/test_phase5_postgres.py",
)
PHASE_5_TABLES = (
    "evaluation_policies",
    "evaluation_feature_specs",
    "evaluation_label_specs",
    "evaluation_blocked_outcomes",
    "evaluation_reports",
    "evaluation_report_snapshots",
    "evaluation_trials",
    "evaluation_folds",
    "evaluation_preprocessing_fits",
    "evaluation_oos_ledger",
    "evaluation_cost_ledger",
    "evaluation_gate_results",
)
PHASE_5_APPEND_ONLY_ERROR = "Phase 5 evaluation records are append-only"
PHASE_6_REQUIRED_PATHS = (
    "docs/PHASE_06_RESEARCH_DECISIONS.md",
    "docs/handoffs/PHASE_07.md",
    "services/api/migrations/versions/0006_phase6_research.py",
    "services/api/src/fable5_api/research.py",
    "services/api/tests/test_phase6_openapi_contract.py",
    "services/api/tests/test_phase6_routes.py",
    "services/data/src/fable5_data/phase6_synthetic.py",
    "services/data/tests/test_phase6_source_contracts.py",
    "services/research/src/fable5_research/artifacts.py",
    "services/research/src/fable5_research/canonical.py",
    "services/research/src/fable5_research/contracts.py",
    "services/research/src/fable5_research/integrity.py",
    "services/research/src/fable5_research/phase5.py",
    "services/research/src/fable5_research/preparation.py",
    "services/research/src/fable5_research/reproduction.py",
    "services/research/src/fable5_research/repository.py",
    "services/research/src/fable5_research/trial_costs.py",
    "services/research/src/fable5_research/workflow.py",
    "services/research/tests",
    "packages/contracts/src/phase6-contract.type-test.ts",
    "tests/test_phase6_migration.py",
    "tests/test_phase6_static.py",
)
PHASE_6_TABLES = (
    "research_pipeline_runs",
    "research_pipeline_snapshot_bindings",
    "research_pipeline_attempts",
    "research_feature_rows",
    "research_score_outputs",
    "research_baseline_comparisons",
    "research_text_extractions",
    "research_text_corroborations",
)
PHASE_6_APPEND_ONLY_ERROR = "Phase 6 research artifacts are append-only"
PHASE_4_CAPABILITIES = {
    "security_master",
    "universe_membership",
    "ohlcv",
    "corporate_actions",
    "delistings",
    "as_reported_fundamentals",
    "trading_calendar",
    "volatility_return_inputs",
    "official_document_event_metadata",
}
PHASE_6_ADDITIVE_CAPABILITIES = {"macro_regime_inputs"}
PHASE_4_RECORD_TYPES = {
    "instrument_identity",
    "listing_identity",
    "universe_membership",
    "ohlcv_bar",
    "corporate_action",
    "delisting_event",
    "as_reported_fundamental",
    "calendar_session",
    "official_document_event",
    "volatility_return_input",
}
PHASE_6_ADDITIVE_RECORD_TYPES = {
    "sector_classification",
    "official_document_content",
    "social_attention",
    "macro_rate_observation",
    "crisis_window_definition",
}
PHASE_6_FIXTURE_SET_VERSION = "phase6-synthetic-pit-fixtures-v2"
PHASE_6_FIXTURE_SET_SHA256 = "010c4edf621f5a75cbb1913a5a513e3c2472e8da9a53b143345b2fb91f6fed5d"
PHASE_6_REQUEST_TIMEOUT_SECONDS = 240
PHASE_6_FAMILY_B_COST_VOLATILITY_PROJECTION_ID = "phase6-family-b-cost-volatility-1e-8-half-even-v1"
PHASE_6_FAMILY_B_COST_VOLATILITY_QUANTUM = "0.00000001"
PHASE_6_FAMILY_B_TRANSACTION_COST_MODEL_ID = (
    "phase5-component-cost-model-v1-with-" + PHASE_6_FAMILY_B_COST_VOLATILITY_PROJECTION_ID
)
PHASE_6_COST_IDENTITY_FIELDS = ("cost_entry_id", "cost_entry_sha256", "ordinal")
PHASE_6_COST_EXACT_FIELDS = (
    "scenario",
    "sample_id",
    "allocation_input_sha256",
    "return_status",
    "fill_status",
    "hard_to_borrow_available",
    "capacity_breached",
)
PHASE_6_COST_DECIMAL_FIELDS = (
    "requested_quantity",
    "filled_quantity",
    "rejected_quantity",
    "unfilled_quantity",
    "gross_return",
    "fee_cost",
    "spread_cost",
    "impact_cost",
    "latency_cost",
    "borrow_cost",
    "capacity_cost",
    "total_cost",
    "net_return",
    "participation_rate",
)
PHASE_4_SCHEMA_VERSIONS = {
    "phase4-canonical-json-v1",
    "phase4-data-snapshot-v1",
    "phase4-raw-observation-v1",
    "phase4-normalized-observation-v1",
    "phase4-observation-revision-v1",
    "phase4-data-quality-v1",
    "phase4-request-fingerprint-v1",
    "phase4-date-only-next-day-v1",
    "phase4-synthetic-pit-adapter-v1",
    "phase4-synthetic-pit-fixtures-v1",
    "phase4-synthetic-test-fixture-rights-v1",
}
PHASE_1_4_MIGRATION_SHA256 = {
    "services/api/migrations/versions/0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "services/api/migrations/versions/0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "services/api/migrations/versions/0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
    "services/api/migrations/versions/0004_phase4_point_in_time_data.py": (
        "78c52c613358708940d88cbd47069bdde9bc857046bf646d7461bd13b57b3008"
    ),
}
PHASE_1_5_MIGRATION_SHA256 = {
    **PHASE_1_4_MIGRATION_SHA256,
    "services/api/migrations/versions/0005_phase5_evaluation.py": (
        "b368edf97c35c5b7d7ac651073a02c204816b638855d3bcae4d7cabf265a1404"
    ),
}
PHASE_5_GATE_IMPLEMENTATION_SHA256 = {
    "canonical.py": "095c174b94778d22feef4a0444279f0fea63d1d6b53b678aac571221faf4a4c0",
    "chronology.py": "dd6418352b96089306ecfc8a026d1be4c217ef220fe818a05c92dc5aa813fa76",
    "costs.py": "7b5a31c165756f99ca33ed72585aa5631d26588f48fb811f5e483dfc7f92273f",
    "engine.py": "eaf99d7295a51b9f49019105fbc9c7272a911fd8cfeaffce8f5d4a7608d0cdc3",
    "evaluation_geometry.py": ("8d66b3e4e31a1e45a13d0c3e57c5e8162a4487cd283fbef2b3a1404c3bdf03ce"),
    "leakage.py": "a7e31285ddf9f376c402fe2dd4651442f513a4ed290f5267e06a17d918efebf1",
    "metrics.py": "b8d21981b98c02f68be6b9393dd486d667882c0415e207d22f8449fac450f2aa",
    "outcomes.py": "28d45549873ca6f805a20c1989e2985b91649ff332a638a11e54fe14d28a2f86",
    "preprocessing.py": ("f8eadbd610aec003ea6700c2141656a34491d1b0e03992274ec8f1dd389d5c34"),
    "statistics.py": "1afa8c4f5e6a3b3e1ba85b525d50b34b86eb3feb1178329bec2d069aedd30907",
}
PHASE_4_BASE_FUNCTION_PROSRC_SHA256 = {
    "phase4_record_type_matches_capability(text,text)": (
        "940e8e9b175cad7e0cc986b97cde39e1ef115022983114bcf73cff9918da4a27"
    ),
    "validate_phase4_snapshot_request()": (
        "bf41f4906b94991731d80fbf1756dbad087081d552acc6d328e6b4eff6cca4af"
    ),
    "validate_phase4_normalized_observation()": (
        "24ae95de6e20c0231ca277d644dd3d518ce2830b00c2a4439877e8da59bf90ed"
    ),
}
PHASE_6_CONFIGURATION_IDS = {
    "phase6-a-pass-v2",
    "phase6-a-fail-cost-v2",
    "phase6-b-pass-v2",
    "phase6-b-fail-crash-v2",
    "phase6-c-pass-v2",
    "phase6-c-fail-corroboration-v2",
}
PHASE_6_FAMILIES = {
    "A_CROSS_SECTIONAL_EQUITY_RANKING",
    "B_TIME_SERIES_MOMENTUM_REGIME",
    "C_OFFICIAL_EVENT_TEXT_OVERLAY",
}
FORBIDDEN_VENDOR_SDK_MODULES = {
    "alpaca",
    "alpaca_trade_api",
    "alpaca_py",
    "bloomberg",
    "ccxt",
    "databento",
    "finnhub",
    "ib_insync",
    "ibapi",
    "polygon",
    "refinitiv",
    "yfinance",
}
FORBIDDEN_PHASE_4_NETWORK_MODULES = {
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "urllib3",
}
PHASE_4_FORBIDDEN_API_TERMS = (
    "feature",
    "label",
    "signal",
    "strategy",
    "model",
    "train",
    "backtest",
    "performance",
    "portfolio",
    "risk",
    "approval",
    "broker",
    "position",
    "order",
    "execution",
    "live",
    "paper",
)
PHASE_5_SYMBOL_PREFIXES = (
    "feature",
    "label",
    "signal",
    "strategy",
    "model",
    "train",
    "backtest",
    "performance",
    "portfolio",
    "risk",
    "approval",
    "broker",
    "position",
    "order",
    "execution",
)
FORBIDDEN_EXECUTABLE_PATTERNS = re.compile(
    r"submit_order|place_order|create_order|/v2/orders|api\.alpaca\.markets|"
    r"alpaca-py|ib_insync|\bibapi\b|\bccxt\b",
    re.IGNORECASE,
)
PHASE_1_ONLY_FORBIDDEN_PATTERNS = re.compile(r"TradingIdeaCard", re.IGNORECASE)


def phase_number(value: str) -> int:
    try:
        phase = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("phase must be 1, 2, 3, 4, 5, or 6") from exc
    if phase not in {1, 2, 3, 4, 5, 6}:
        raise argparse.ArgumentTypeError("phase must be 1, 2, 3, 4, 5, or 6")
    return phase


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def phase6_cost_entries_match(
    left: object,
    right: object,
    *,
    require_identity: bool,
) -> bool:
    """Compare cost evidence using the Phase 5 Decimal semantics, not JSON text scale."""

    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    exact_fields = PHASE_6_COST_EXACT_FIELDS + (
        PHASE_6_COST_IDENTITY_FIELDS if require_identity else ()
    )
    if any(left.get(field) != right.get(field) for field in exact_fields):
        return False
    try:
        return all(
            Decimal(str(left.get(field))) == Decimal(str(right.get(field)))
            for field in PHASE_6_COST_DECIMAL_FIELDS
        )
    except (ArithmeticError, ValueError):
        return False


def enum_string_values(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.value.value
                for child in node.body
                if isinstance(child, ast.Assign)
                and isinstance(child.value, ast.Constant)
                and isinstance(child.value.value, str)
            }
    raise AssertionError(f"Missing enum {class_name} in {path.relative_to(ROOT)}")


def imported_module_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def declared_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def assigned_call_keyword(path: Path, assignment_name: str, keyword_name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == assignment_name
                for target in node.targets
            )
            and isinstance(node.value, ast.Call)
        ):
            for keyword in node.value.keywords:
                if keyword.arg == keyword_name:
                    value = ast.literal_eval(keyword.value)
                    if isinstance(value, str):
                        return value
    raise AssertionError(
        f"Missing string keyword {assignment_name}.{keyword_name} in {path.relative_to(ROOT)}"
    )


def resolve_openapi_schema(
    schema: dict[str, object], components: dict[str, dict[str, object]]
) -> dict[str, object]:
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
        return components[reference.rsplit("/", 1)[1]]
    return schema


def canonical_gates() -> str:
    prompt = normalized(ROOT / "FABLE5_BUILD_PROMPT.md")
    start = prompt.index(GATE_START)
    end = prompt.index(GATE_END, start) + len(GATE_END)
    gates = prompt[start:end]
    digest = hashlib.sha256(gates.encode()).hexdigest()
    if digest != GATE_SHA256:
        raise AssertionError(f"Unexpected hard-gate source block hash: {digest}")
    return gates


def verify_static(phase: int = 1) -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Phase 1 paths: {', '.join(missing)}")
    if phase >= 2:
        missing_phase2 = [path for path in PHASE_2_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase2:
            raise AssertionError(f"Missing Phase 2 paths: {', '.join(missing_phase2)}")
        fixture_root = ROOT / "services" / "extraction" / "tests" / "fixtures"
        missing_fixtures = [name for name in PHASE_2_FIXTURES if not (fixture_root / name).exists()]
        if missing_fixtures:
            raise AssertionError(
                f"Missing synthetic Phase 2 fixtures: {', '.join(missing_fixtures)}"
            )
    if phase >= 3:
        missing_phase3 = [path for path in PHASE_3_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase3:
            raise AssertionError(f"Missing Phase 3 paths: {', '.join(missing_phase3)}")
    if phase >= 4:
        missing_phase4 = [path for path in PHASE_4_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase4:
            raise AssertionError(f"Missing Phase 4 paths: {', '.join(missing_phase4)}")
    if phase >= 5:
        missing_phase5 = [path for path in PHASE_5_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase5:
            raise AssertionError(f"Missing Phase 5 paths: {', '.join(missing_phase5)}")
    if phase >= 6:
        missing_phase6 = [path for path in PHASE_6_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase6:
            raise AssertionError(f"Missing Phase 6 paths: {', '.join(missing_phase6)}")

    gates = canonical_gates()
    for filename in ("AGENTS.md", "CLAUDE.md"):
        body = normalized(ROOT / filename)
        if not body.startswith(gates + "\n\n"):
            raise AssertionError(f"{filename} does not begin with the verbatim hard gates")

    if normalized(ROOT / "RESEARCH_SUPPLEMENT.md") != normalized(
        ROOT / "docs" / "RESEARCH_SUPPLEMENT.md"
    ):
        raise AssertionError("docs/RESEARCH_SUPPLEMENT.md drifted from its source")

    scan_roots = [
        ROOT / "services",
        ROOT / "packages",
        ROOT / "pyproject.toml",
        ROOT / "package.json",
    ]
    violations: list[str] = []
    for scan_root in scan_roots:
        candidates = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for path in candidates:
            if not path.is_file() or "tests" in path.parts:
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".toml"}:
                continue
            body = path.read_text(encoding="utf-8")
            patterns = [FORBIDDEN_EXECUTABLE_PATTERNS]
            if phase == 1:
                patterns.append(PHASE_1_ONLY_FORBIDDEN_PATTERNS)
            for pattern in patterns:
                match = pattern.search(body)
                if match:
                    violations.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
                    break
    if violations:
        raise AssertionError(f"Forbidden code found for Phase {phase}: " + "; ".join(violations))

    if phase >= 2:
        migration = normalized(
            ROOT / "services/api/migrations/versions/0002_phase2_source_extraction.py"
        )
        if 'down_revision: str | None = "0001_phase1"' not in migration:
            raise AssertionError("Phase 2 migration must revise immutable Phase 1 revision")
        for table in PHASE_2_TABLES:
            if table not in migration:
                raise AssertionError(f"Phase 2 migration is missing {table}")
        for dockerfile in ("services/api/Dockerfile", "services/jobs/Dockerfile"):
            if "COPY services/extraction ./services/extraction" not in normalized(
                ROOT / dockerfile
            ):
                raise AssertionError(f"{dockerfile} does not package the extraction domain")
        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        components = openapi["components"]["schemas"]
        card_properties = components["TradingIdeaCard"]["properties"]
        evidence_refs = {
            "asset_class": "AssetClassEvidence",
            "forecast_horizon": "ForecastHorizonEvidence",
            "signal_family": "SignalFamilyEvidence",
            "execution_style": "ExecutionStyleEvidence",
            "required_data": "RequiredDataEvidence",
            "risk_assumptions": "RiskAssumptionsEvidence",
        }
        for field, component in evidence_refs.items():
            expected = {"$ref": f"#/components/schemas/{component}"}
            if card_properties[field] != expected:
                raise AssertionError(f"Phase 2 card field {field} is not field-specific")
        if "TextEvidence" in components or "ListEvidence" in components:
            raise AssertionError("Generic cross-field Phase 2 evidence schemas remain public")
        for request_schema in ("SourceIntakeRequest", "SourceCorrectionRequest"):
            properties = components[request_schema]["properties"]
            if "supplied_at_utc" in properties:
                raise AssertionError(f"{request_schema} exposes the server-owned timestamp")
            if properties["raw_text"].get("type") != "string" or "anyOf" in properties["raw_text"]:
                raise AssertionError(f"{request_schema}.raw_text still accepts explicit null")
        source_version = components["SourceVersion"]
        if "supplied_at_utc" not in source_version["required"]:
            raise AssertionError("SourceVersion does not expose its database-owned timestamp")

        domain_paths = {
            path: operations
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/")
        }
        if not domain_paths:
            raise AssertionError("Phase 2 OpenAPI paths are missing")
        for path, operations in domain_paths.items():
            if set(operations) - {"get", "post"}:
                raise AssertionError(
                    f"Phase 2 route allows mutation beyond create/read/list: {path}"
                )
        forbidden_path_terms = ("signal", "backtest", "broker", "position", "order", "live")
        for path in domain_paths:
            if any(term in path.lower() for term in forbidden_path_terms):
                raise AssertionError(f"Forbidden Phase 2 API path: {path}")

        handoff = normalized(ROOT / "docs/handoffs/PHASE_03.md")
        headings = re.findall(r"^## .+$", handoff, flags=re.MULTILINE)
        required_headings = [
            "## Objective and explicit exclusions",
            "## Inputs and source authority",
            "## Files/directories in scope",
            "## Contracts and invariants",
            "## Implementation units",
            "## Acceptance tests",
            "## Data/security posture",
            "## Migration/rollback",
            "## Handoff report",
            "## Stop condition",
        ]
        if headings != required_headings:
            raise AssertionError("Phase 3 handoff sections are incomplete or out of order")
        contract = handoff.split("## Contracts and invariants", 1)[1].split(
            "## Implementation units", 1
        )[0]
        vocabulary_table = contract.split("Priority prose", 1)[0]
        verdicts = set(re.findall(r"`([A-Z][A-Z_]+)`", vocabulary_table))
        expected_verdicts = {
            "BUILD_RESEARCH",
            "DEFER",
            "DEFER_READ_ONLY",
            "REJECT_PLATFORM",
            "NON_TESTABLE",
        }
        if verdicts != expected_verdicts or "`REJECT`" in contract:
            raise AssertionError("Phase 3 handoff machine-verdict vocabulary is not closed")

    if phase >= 3:
        mapper_path = ROOT / "services/mapping/src/fable5_mapping/mapper.py"
        rules_path = ROOT / "services/mapping/src/fable5_mapping/rules.py"
        mapper_sha256 = hashlib.sha256(normalized(mapper_path).encode("utf-8")).hexdigest()
        evaluator_identity = assigned_call_keyword(
            rules_path,
            "CURRENT_RULE_SET",
            "evaluator_identity",
        )
        expected_evaluator_identity = f"fable5_mapping.mapper.sha256:{mapper_sha256}"
        if evaluator_identity != expected_evaluator_identity:
            raise AssertionError(
                "Phase 3 rule-set hash does not identify the exact executable mapper source"
            )

        migration_path = ROOT / "services/api/migrations/versions/0003_phase3_canon_mapping.py"
        migration = normalized(migration_path)
        if 'down_revision: str | None = "0002_phase2"' not in migration:
            raise AssertionError("Phase 3 migration must directly revise immutable Phase 2")
        for table in PHASE_3_TABLES:
            if table not in migration:
                raise AssertionError(f"Phase 3 migration is missing {table}")
        for required_constraint in (
            "mapper_rule_set_version",
            "mapper_rule_set_sha256",
            "matched_rule_ids",
            "reason_codes",
            "CREATE FUNCTION validate_phase3_mapping_lineage()",
            "CREATE CONSTRAINT TRIGGER research_mapping_versions_corroboration_set",
            "CREATE CONSTRAINT TRIGGER mapping_official_corroborations_exact_set",
            "CREATE CONSTRAINT TRIGGER card_official_corroborations_mapping_set",
            "DEFERRABLE INITIALLY DEFERRED",
            "CREATE FUNCTION reject_phase3_finalized_corroboration_append()",
            "CREATE TRIGGER card_official_corroborations_phase3_finalized",
            "CREATE TRIGGER mapping_official_corroborations_phase3_finalized",
            "CREATE TRIGGER {table}_immutable",
            "CREATE TRIGGER {table}_no_truncate",
        ):
            if required_constraint not in migration:
                raise AssertionError(
                    f"Phase 3 migration is missing mapping invariant {required_constraint}"
                )

        api_dockerfile = normalized(ROOT / "services/api/Dockerfile")
        if "COPY services/mapping ./services/mapping" not in api_dockerfile:
            raise AssertionError("services/api/Dockerfile does not package the mapping domain")

        for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
            entrypoint_source = normalized(ROOT / entrypoint)
            if "FABLE5_VERIFY_PHASE" not in entrypoint_source or "--phase" not in entrypoint_source:
                raise AssertionError(
                    f"{entrypoint} does not validate and forward FABLE5_VERIFY_PHASE"
                )
        ci = normalized(ROOT / ".github/workflows/ci.yml")
        ci_phases = [int(value) for value in re.findall(r"--phase\s+([1-6])", ci)]
        if sum(selected >= phase for selected in ci_phases) < 2:
            raise AssertionError(
                f"CI does not run both static and full verification at or beyond Phase {phase}"
            )

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        components = openapi["components"]["schemas"]
        expected_mapping_paths = {
            "/v1/cards/{card_id}/mappings": {"post"},
            "/v1/mappings": {"get"},
            "/v1/mappings/{mapping_id}": {"get"},
        }
        mapping_paths = {
            path: {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            for path, operations in openapi["paths"].items()
            if "mapping" in path
        }
        if mapping_paths != expected_mapping_paths:
            raise AssertionError(f"Phase 3 mapping paths/methods are not exact: {mapping_paths}")
        mapping_create = openapi["paths"]["/v1/cards/{card_id}/mappings"]["post"]
        if "requestBody" in mapping_create:
            raise AssertionError("Phase 3 mapping creation must not accept a request body")

        domain_paths = {
            path: operations
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/")
        }
        for path, operations in domain_paths.items():
            methods = {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            if methods - {"get", "post"}:
                raise AssertionError(f"Phase 3 API exposes a mutation method: {path} {methods}")
        forbidden_path_terms = (
            "signal",
            "backtest",
            "broker",
            "position",
            "order",
            "live",
            "paper",
        )
        for path in domain_paths:
            if any(term in path.lower() for term in forbidden_path_terms):
                raise AssertionError(f"Forbidden Phase 3 API path: {path}")
        dormant_directories = ["services/risk", "strategy_specs"]
        if phase < 5:
            dormant_directories.append("services/backtester")
        for dormant_directory in dormant_directories:
            entries = sorted(path.name for path in (ROOT / dormant_directory).iterdir())
            if entries != ["README.md"]:
                raise AssertionError(
                    f"Phase {phase} created a forbidden scaffold in {dormant_directory}"
                )

        for component in (
            "CanonicalFamily",
            "ResearchVerdict",
            "MappingRuleId",
            "MappingReasonCode",
        ):
            if component not in components:
                raise AssertionError(f"Phase 3 OpenAPI is missing {component}")
        if set(components["CanonicalFamily"].get("enum", [])) != PHASE_3_CANONICAL_FAMILIES:
            raise AssertionError("CanonicalFamily OpenAPI vocabulary is not closed")
        if set(components["ResearchVerdict"].get("enum", [])) != PHASE_3_VERDICTS:
            raise AssertionError("ResearchVerdict OpenAPI vocabulary is not closed")
        model_reasons = enum_string_values(
            ROOT / "services/mapping/src/fable5_mapping/models.py", "MappingReasonCode"
        )
        if not PHASE_3_REQUIRED_REASONS <= model_reasons:
            missing_reasons = sorted(PHASE_3_REQUIRED_REASONS - model_reasons)
            raise AssertionError(
                f"MappingReasonCode is missing required reasons: {missing_reasons}"
            )
        if set(components["MappingReasonCode"].get("enum", [])) != model_reasons:
            raise AssertionError("MappingReasonCode OpenAPI vocabulary drifted from its model")
        model_rule_ids = enum_string_values(
            ROOT / "services/mapping/src/fable5_mapping/models.py", "MappingRuleId"
        )
        if set(components["MappingRuleId"].get("enum", [])) != model_rule_ids:
            raise AssertionError("MappingRuleId OpenAPI vocabulary drifted from its model")

        for component in ("ResearchMapping", "MappingWithRationale"):
            if component not in components:
                raise AssertionError(f"Phase 3 OpenAPI is missing {component}")
        mapping_schema = components["ResearchMapping"]
        mapping_properties = mapping_schema["properties"]
        mapping_required = set(mapping_schema.get("required", []))
        for field in (
            "canonical_family",
            "verdict",
            "matched_rule_ids",
            "reason_codes",
            "mapper_rule_set_version",
            "mapper_rule_set_sha256",
        ):
            if field not in mapping_properties or field not in mapping_required:
                raise AssertionError(f"ResearchMapping is missing required field {field}")
        if "#/components/schemas/CanonicalFamily" not in json.dumps(
            mapping_properties["canonical_family"]
        ):
            raise AssertionError("ResearchMapping.canonical_family is not closed")
        if "#/components/schemas/ResearchVerdict" not in json.dumps(mapping_properties["verdict"]):
            raise AssertionError("ResearchMapping.verdict is not closed")
        if "#/components/schemas/MappingReasonCode" not in json.dumps(
            mapping_properties["reason_codes"]
        ):
            raise AssertionError("ResearchMapping.reason_codes is not closed")
        if "#/components/schemas/MappingRuleId" not in json.dumps(
            mapping_properties["matched_rule_ids"]
        ):
            raise AssertionError("ResearchMapping.matched_rule_ids is not closed")
        hash_schema = resolve_openapi_schema(
            mapping_properties["mapper_rule_set_sha256"], components
        )
        if hash_schema.get("pattern") != "^[0-9a-f]{64}$":
            raise AssertionError("ResearchMapping mapper rule-set hash is not a SHA-256 schema")
        nested = components["MappingWithRationale"]["properties"]
        if nested.get("mapping") != {"$ref": "#/components/schemas/ResearchMapping"}:
            raise AssertionError(
                "MappingWithRationale.mapping is not generated from ResearchMapping"
            )
        if "rationale" not in nested:
            raise AssertionError("MappingWithRationale is missing its rationale artifact")
        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        if "MappingWithRationale:" not in generated or "ResearchMapping:" not in generated:
            raise AssertionError("Generated TypeScript mapping contracts are missing")
        decisions = normalized(ROOT / "docs/PHASE_03_MAPPING_DECISIONS.md")
        if f"`{PHASE_3_RULE_SET_SHA256}`" not in decisions:
            raise AssertionError("Phase 3 decisions do not freeze the canonical rule-set hash")

    if phase >= 4:
        migration_authority = (
            PHASE_1_5_MIGRATION_SHA256 if phase >= 6 else PHASE_1_4_MIGRATION_SHA256
        )
        immutable_migrations = {
            path: digest
            for path, digest in migration_authority.items()
            if phase >= 5 or "0004_phase4" not in path
        }
        for relative_path, expected_sha256 in immutable_migrations.items():
            actual_sha256 = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise AssertionError(
                    f"Immutable earlier migration changed: {relative_path} ({actual_sha256})"
                )

        contracts_path = ROOT / "services/data/src/fable5_data/contracts.py"
        contracts = normalized(contracts_path)
        canonical = normalized(ROOT / "services/data/src/fable5_data/canonical.py")
        decisions = normalized(ROOT / "docs/PHASE_04_DATA_DECISIONS.md")
        migration = normalized(
            ROOT / "services/api/migrations/versions/0004_phase4_point_in_time_data.py"
        )
        if 'down_revision: str | None = "0003_phase3"' not in migration:
            raise AssertionError("Phase 4 migration must directly revise immutable Phase 3")
        for table in PHASE_4_TABLES:
            if table not in migration:
                raise AssertionError(f"Phase 4 migration is missing {table}")
        for required_constraint in (
            "CREATE FUNCTION validate_phase4_snapshot_request()",
            "CREATE FUNCTION validate_phase4_observation_envelope()",
            "CREATE FUNCTION validate_phase4_raw_observation()",
            "CREATE FUNCTION validate_phase4_observation_revision()",
            "CREATE FUNCTION validate_phase4_normalized_observation()",
            "CREATE FUNCTION validate_phase4_snapshot_constituent()",
            "CREATE FUNCTION validate_phase4_quality_finding()",
            "CREATE FUNCTION validate_phase4_snapshot_manifest()",
            "CREATE CONSTRAINT TRIGGER data_snapshots_manifest_required",
            "CREATE FUNCTION reject_phase4_data_mutation()",
            "CREATE TRIGGER {table}_immutable",
            "CREATE TRIGGER {table}_no_truncate",
            "Phase 4 data records are append-only",
        ):
            if required_constraint not in migration:
                raise AssertionError(
                    f"Phase 4 migration is missing invariant {required_constraint}"
                )

        actual_capabilities = enum_string_values(contracts_path, "DataCapability")
        allowed_capability_vocabularies = {
            frozenset(PHASE_4_CAPABILITIES),
            frozenset(PHASE_4_CAPABILITIES | PHASE_6_ADDITIVE_CAPABILITIES),
        }
        if frozenset(actual_capabilities) not in allowed_capability_vocabularies:
            raise AssertionError(
                f"Phase 4/6 capability vocabulary is not exact: {sorted(actual_capabilities)}"
            )
        if actual_capabilities != PHASE_4_CAPABILITIES:
            if (
                actual_capabilities != PHASE_4_CAPABILITIES | PHASE_6_ADDITIVE_CAPABILITIES
                or "PHASE4_DATA_CAPABILITIES: Final = tuple(" not in contracts
                or "if item is not DataCapability.MACRO_REGIME_INPUTS" not in contracts
            ):
                raise AssertionError(
                    "Phase 6 additive capability changed the frozen Phase 4 capability set"
                )
        if phase >= 6 and actual_capabilities != (
            PHASE_4_CAPABILITIES | PHASE_6_ADDITIVE_CAPABILITIES
        ):
            raise AssertionError("Phase 6 macro-regime capability is missing")
        actual_record_types = enum_string_values(contracts_path, "DataRecordType")
        expected_record_types = PHASE_4_RECORD_TYPES | (
            PHASE_6_ADDITIVE_RECORD_TYPES if phase >= 6 else set()
        )
        if actual_record_types != expected_record_types:
            raise AssertionError(
                f"Phase 4/6 record-type vocabulary is not exact: {sorted(actual_record_types)}"
            )
        for version in PHASE_4_SCHEMA_VERSIONS:
            if version not in contracts + canonical or f"`{version}`" not in decisions:
                raise AssertionError(f"Phase 4 schema/version identity is not frozen: {version}")

        for required_contract in (
            "class SnapshotCreateRequest(StrictModel):",
            "class AdapterAvailableResult(StrictModel):",
            "class AdapterUnavailableResult(StrictModel):",
            "class RawObservationDraft(ObservationEnvelopeDraft):",
            "class ObservationRevisionDraft(ObservationEnvelopeDraft):",
            "class NormalizedObservationDraft(ObservationEnvelopeDraft):",
            "class DataSnapshot(",
            "class SnapshotBundle(StrictModel):",
            "class DataQualityFindingDraft(StrictModel):",
            "PHASE4_SCHEMA_CONSTANTS = MappingProxyType(",
            "item.available_at > self.request.as_of_utc",
        ):
            if required_contract not in contracts:
                raise AssertionError(f"Phase 4 contract invariant is missing: {required_contract}")

        data_source_root = ROOT / "services/data/src/fable5_data"
        for path in data_source_root.rglob("*.py"):
            if path.stem.casefold().startswith(PHASE_5_SYMBOL_PREFIXES):
                raise AssertionError(
                    f"Phase 5+ data module is present during Phase 4: {path.relative_to(ROOT)}"
                )
            forbidden_symbols = sorted(
                symbol
                for symbol in declared_symbols(path)
                if symbol.casefold().startswith(PHASE_5_SYMBOL_PREFIXES)
            )
            if forbidden_symbols:
                raise AssertionError(
                    "Phase 5+ symbol is present in the Phase 4 data package: "
                    f"{path.relative_to(ROOT)} {forbidden_symbols}"
                )
            imported = imported_module_roots(path)
            forbidden = imported & (
                FORBIDDEN_VENDOR_SDK_MODULES | FORBIDDEN_PHASE_4_NETWORK_MODULES
            )
            if forbidden:
                raise AssertionError(
                    "Phase 4 data package imports a provider SDK or network client: "
                    f"{path.relative_to(ROOT)} {sorted(forbidden)}"
                )
        for source_root in (
            ROOT / "services/api/src",
            ROOT / "services/extraction/src",
            ROOT / "services/mapping/src",
        ):
            for path in source_root.rglob("*.py"):
                forbidden = imported_module_roots(path) & FORBIDDEN_VENDOR_SDK_MODULES
                if forbidden:
                    raise AssertionError(
                        "A Phase 1-4 production package imports a provider SDK: "
                        f"{path.relative_to(ROOT)} {sorted(forbidden)}"
                    )

        for dockerfile in ("services/api/Dockerfile", "services/jobs/Dockerfile"):
            if "COPY services/data ./services/data" not in normalized(ROOT / dockerfile):
                raise AssertionError(f"{dockerfile} does not package the Phase 4 data domain")

        snapshot_api = normalized(ROOT / "services/api/src/fable5_api/data_snapshots.py")
        resolver_evidence_values = ["SyntheticPointInTimeAdapter.for_mapping(mapping)"]
        resolver_evidence_values.append(
            "configured_adapter_resolver=resolve_configured_adapter"
            if phase >= 6
            else "adapter_resolver=resolve_adapter"
        )
        for resolver_evidence in resolver_evidence_values:
            if resolver_evidence not in snapshot_api:
                raise AssertionError(
                    "Default Phase 4 workflow does not server-resolve mapping-bound synthetic "
                    f"data: {resolver_evidence}"
                )

        adapter_test = normalized(ROOT / "services/data/tests/test_adapters.py")
        for evidence in (
            'assert calls == {"factory": 0, "transport": 0}',
            "AdapterUnavailableReason.CREDENTIALS_UNAVAILABLE",
            "assert planted_secret not in rendered",
        ):
            if evidence not in adapter_test:
                raise AssertionError(
                    f"Phase 4 credential-unavailable zero-network evidence is missing: {evidence}"
                )

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        components = openapi["components"]["schemas"]
        expected_snapshot_paths = {
            "/v1/data-snapshots": {"get", "post"},
            "/v1/data-snapshots/{snapshot_id}": {"get"},
        }
        snapshot_paths = {
            path: {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/data-snapshots")
        }
        if snapshot_paths != expected_snapshot_paths:
            raise AssertionError(f"Phase 4 snapshot paths/methods are not exact: {snapshot_paths}")
        for component in (
            "AdapterUnavailableResult",
            "DataCapability",
            "DataSnapshot",
            "SnapshotBuildBlockedResult",
            "SnapshotBundle",
            "SnapshotCreateRequest",
        ):
            if component not in components:
                raise AssertionError(f"Phase 4 OpenAPI is missing {component}")
        expected_openapi_capabilities = PHASE_4_CAPABILITIES | (
            PHASE_6_ADDITIVE_CAPABILITIES if phase >= 6 else set()
        )
        if set(components["DataCapability"].get("enum", [])) != expected_openapi_capabilities:
            raise AssertionError("Phase 4/6 DataCapability OpenAPI vocabulary is not exact")
        request_schema = components["SnapshotCreateRequest"]
        request_fields = set(request_schema.get("properties", {}))
        expected_request_fields = {
            "mapping_id",
            "as_of_utc",
            "capability",
            "mock_configuration_id",
        }
        if (
            request_fields != expected_request_fields
            or set(request_schema.get("required", [])) != expected_request_fields
        ):
            raise AssertionError(
                "SnapshotCreateRequest accepts fields beyond server-resolvable identities"
            )
        if request_schema.get("additionalProperties") is not False:
            raise AssertionError(
                "SnapshotCreateRequest does not reject client-authoritative extras"
            )

        domain_paths = {
            path: operations
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/")
        }
        for path, operations in domain_paths.items():
            methods = {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            if methods - {"get", "post"}:
                raise AssertionError(f"Phase 4 API exposes a mutation method: {path} {methods}")
            if any(term in path.casefold() for term in PHASE_4_FORBIDDEN_API_TERMS):
                raise AssertionError(f"Forbidden Phase 5+ or execution API path: {path}")

        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        for generated_contract in (
            "AdapterUnavailableResult:",
            "DataSnapshot:",
            "SnapshotBuildBlockedResult:",
            "SnapshotBundle:",
            "SnapshotCreateRequest:",
            '"/v1/data-snapshots"',
            '"/v1/data-snapshots/{snapshot_id}"',
        ):
            if generated_contract not in generated:
                raise AssertionError(
                    f"Generated TypeScript Phase 4 contract is missing {generated_contract}"
                )

        secret_pattern = re.compile(r"\b(?:sk|api[_-]?key)[-_][A-Za-z0-9_-]{8,}\b", re.IGNORECASE)
        secret_surfaces = (
            ROOT / "services/data/src/fable5_data/fixtures/phase4_synthetic_pit_v1.json",
            ROOT / "packages/contracts/openapi.json",
            ROOT / "packages/contracts/src/api.generated.ts",
        )
        for path in secret_surfaces:
            match = secret_pattern.search(path.read_text(encoding="utf-8"))
            if match:
                raise AssertionError(
                    f"Credential-shaped content leaked into {path.relative_to(ROOT)}"
                )

    if phase >= 5:
        migration = normalized(ROOT / "services/api/migrations/versions/0005_phase5_evaluation.py")
        if 'down_revision: str | None = "0004_phase4"' not in migration:
            raise AssertionError("Phase 5 migration must directly revise immutable Phase 4")
        for table in PHASE_5_TABLES:
            if table not in migration:
                raise AssertionError(f"Phase 5 migration is missing {table}")
        for required_append_only_evidence in (
            "CREATE TRIGGER {table}_immutable",
            "CREATE TRIGGER {table}_no_truncate",
            PHASE_5_APPEND_ONLY_ERROR,
        ):
            if required_append_only_evidence not in migration:
                raise AssertionError(
                    "Phase 5 migration is missing append-only evidence "
                    f"{required_append_only_evidence}"
                )

        for dockerfile in ("services/api/Dockerfile", "services/jobs/Dockerfile"):
            if "COPY services/backtester ./services/backtester" not in normalized(
                ROOT / dockerfile
            ):
                raise AssertionError(f"{dockerfile} does not package the Phase 5 evaluator")

        compose = normalized(ROOT / "compose.yaml")
        if "FABLE5_CODE_VERSION_GIT_SHA: ${FABLE5_CODE_VERSION_GIT_SHA:-}" not in compose:
            raise AssertionError("Compose does not pass through the optional server-owned git SHA")
        api_config = normalized(ROOT / "services/api/src/fable5_api/config.py")
        if 'pattern=r"^[0-9a-f]{40}$"' not in api_config:
            raise AssertionError("API configuration does not strictly validate the Phase 5 git SHA")

        backtester_root = ROOT / "services/backtester/src/fable5_backtester"
        for path in backtester_root.rglob("*.py"):
            forbidden = imported_module_roots(path) & (
                FORBIDDEN_VENDOR_SDK_MODULES | FORBIDDEN_PHASE_4_NETWORK_MODULES
            )
            if forbidden:
                raise AssertionError(
                    "Phase 5 evaluator imports a provider SDK or network client: "
                    f"{path.relative_to(ROOT)} {sorted(forbidden)}"
                )

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        evaluation_paths = {
            path: {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/evaluation")
        }
        if not evaluation_paths:
            raise AssertionError("Phase 5 evaluation API paths are missing")
        for path, methods in evaluation_paths.items():
            if not methods or methods - {"get", "post"}:
                raise AssertionError(
                    f"Phase 5 evaluation API is not create/read/list only: {path} {methods}"
                )
        forbidden_later_phase_paths = (
            "signal",
            "strategy",
            "portfolio",
            "position",
            "broker",
            "order",
            "execution",
            "approval",
            "paper",
            "live",
        )
        for path in openapi["paths"]:
            if any(term in path.casefold() for term in forbidden_later_phase_paths):
                raise AssertionError(f"Phase 6/7 capability leaked into the Phase 5 API: {path}")

        phase5_surfaces: tuple[Path, ...] = (
            ROOT / "services/api/src/fable5_api/evaluations.py",
            ROOT / "services/api/migrations/versions/0005_phase5_evaluation.py",
            ROOT / "packages/contracts/openapi.json",
            ROOT / "packages/contracts/src/api.generated.ts",
        )
        phase5_surfaces += tuple(backtester_root.rglob("*.py"))
        for path in phase5_surfaces:
            if "APPROVED_PAPER" in path.read_text(encoding="utf-8"):
                raise AssertionError(
                    f"Phase 7 approval state leaked into Phase 5: {path.relative_to(ROOT)}"
                )
        forbidden_later_phase_modules = {
            "signal",
            "strategy",
            "signals",
            "strategies",
            "portfolio",
            "positions",
            "brokers",
            "orders",
            "execution",
            "approvals",
            "paper",
            "live",
        }
        for path in backtester_root.rglob("*.py"):
            module_name = path.stem.casefold()
            if (
                module_name in forbidden_later_phase_modules
                or "strategy" in module_name
                or module_name.endswith("_pipeline")
            ):
                raise AssertionError(
                    f"Phase 6/7 module leaked into Phase 5: {path.relative_to(ROOT)}"
                )
        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        if '"/v1/evaluation' not in generated:
            raise AssertionError("Generated TypeScript Phase 5 evaluation contracts are missing")
        for schema in (
            "BlockedEvaluationOutcome",
            "ResearchReturnStatus",
            "ResolvedSourceObservation",
            "SampleSourceLineage",
        ):
            if schema not in generated:
                raise AssertionError(f"Generated TypeScript contract is missing {schema}")

    if phase >= 6:
        migration = normalized(ROOT / "services/api/migrations/versions/0006_phase6_research.py")
        if 'down_revision: str | None = "0005_phase5"' not in migration:
            raise AssertionError("Phase 6 migration must directly revise immutable Phase 5")
        for table in PHASE_6_TABLES:
            if table not in migration:
                raise AssertionError(f"Phase 6 migration is missing {table}")
        for required_migration_evidence in (
            "CREATE FUNCTION reject_phase6_research_mutation()",
            "CREATE TRIGGER {table}_immutable",
            "CREATE TRIGGER {table}_no_truncate",
            "CREATE FUNCTION validate_phase6_payload_columns()",
            "CREATE FUNCTION validate_phase6_research_pipeline_run()",
            "phase4_record_type_matches_capability",
            "validate_phase4_snapshot_request",
            "validate_phase5_report_source_lineage_phase5_base",
            "social_attention",
            "macro_regime_inputs",
            "macro_rate_observation",
            "crisis_window_definition",
            "social_source_reference",
            "official_source_reference",
            PHASE_6_APPEND_ONLY_ERROR,
        ):
            if required_migration_evidence not in migration:
                raise AssertionError(
                    "Phase 6 migration is missing fail-closed evidence "
                    f"{required_migration_evidence}"
                )

        api_dockerfile = normalized(ROOT / "services/api/Dockerfile")
        if "COPY services/research ./services/research" not in api_dockerfile:
            raise AssertionError("services/api/Dockerfile does not package the Phase 6 domain")

        research_root = ROOT / "services/research/src/fable5_research"
        for path in research_root.rglob("*.py"):
            forbidden = imported_module_roots(path) & (
                FORBIDDEN_VENDOR_SDK_MODULES | FORBIDDEN_PHASE_4_NETWORK_MODULES
            )
            if forbidden:
                raise AssertionError(
                    "Phase 6 research imports a provider SDK or network client: "
                    f"{path.relative_to(ROOT)} {sorted(forbidden)}"
                )

        contracts_path = research_root / "contracts.py"
        contracts = normalized(contracts_path)
        phase5_bridge = normalized(research_root / "phase5.py")
        actual_configuration_ids = enum_string_values(
            contracts_path,
            "ResearchConfigurationId",
        )
        if actual_configuration_ids != PHASE_6_CONFIGURATION_IDS:
            raise AssertionError(
                "Phase 6 deterministic configuration identity vocabulary is not exact: "
                f"{sorted(actual_configuration_ids)}"
            )
        for required_contract in (
            "class ResearchPipelineSpecification(StrictModel):",
            "class PreparedRegimeEvidence(StrictModel):",
            "class ResearchConfirmationInterval(StrictModel):",
            "class ResearchBoundaryExclusion(StrictModel):",
            "class FamilyAEvidence(StrictModel):",
            "class FamilyBEvidence(StrictModel):",
            "class FamilyCEvidence(StrictModel):",
            "class Phase5EvaluationLink(StrictModel):",
            "class ResearchLedgerCell(StrictModel):",
            "class ResearchModelOutputSet(StrictModel):",
            "class ResearchTrialEconomics(StrictModel):",
            "class PreparedPipelineReproductionAudit(StrictModel):",
            "class ResearchRunArtifact(StrictModel):",
            "class ResearchTransformTrainingSample(StrictModel):",
            "phase6-long-flat-weight-times-label-quantized-v1",
            "phase6-research-artifact-v2",
            "phase6-research-specification-v2",
            "phase6-prepared-research-pipeline-v2",
            "phase6-deterministic-research-fixtures-v2",
            "phase6-prepared-regime-evidence-v2",
            "phase6-label-blind-confirmation-interval-v1",
            "rate_regime_source_unavailable",
            "crisis_window_geometry_unavailable",
            "structured_text_extraction_only",
            "structured_features_only",
            "no_image_candlestick_or_named_pattern_classifier",
            "pass_research_is_not_paper_approval",
            "no_real_performance_claimed",
            "paper_approval_granted: Literal[False]",
            "Synthetic research only; no real performance or investment advice.",
        ):
            if required_contract not in contracts:
                raise AssertionError(f"Phase 6 contract invariant is missing: {required_contract}")
        for phase5_bridge_evidence in (
            "build_phase5_inputs",
            "build_phase5_policy",
            "REGISTERED_POLICY",
            "PASS_RESEARCH is a research result and is not paper approval.",
            "PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA",
            "_phase5_rows_with_real_confirmation",
            "phase6_model_output_sha256",
            "phase6_ledger_cell_set_sha256",
        ):
            if phase5_bridge_evidence not in phase5_bridge:
                raise AssertionError(
                    "Phase 6 does not bind research evidence to the unchanged Phase 5 engine: "
                    f"{phase5_bridge_evidence}"
                )

        phase6_data_contracts = normalized(ROOT / "services/data/src/fable5_data/contracts.py")
        phase6_data_fixtures = normalized(
            ROOT / "services/data/tests/test_phase6_source_contracts.py"
        )
        decisions = normalized(ROOT / "docs/PHASE_06_RESEARCH_DECISIONS.md")
        for exact_fixture_evidence in (
            PHASE_6_FIXTURE_SET_VERSION,
            PHASE_6_FIXTURE_SET_SHA256,
            "1,198 deterministic records",
        ):
            if exact_fixture_evidence not in decisions:
                raise AssertionError(
                    f"Phase 6 decisions omit exact v2 fixture evidence: {exact_fixture_evidence}"
                )
        if (
            PHASE_6_FIXTURE_SET_VERSION not in phase6_data_contracts
            or PHASE_6_FIXTURE_SET_SHA256 not in phase6_data_fixtures
        ):
            raise AssertionError("Phase 6 v2 fixture version/hash is not frozen in tests")

        integrity = normalized(research_root / "integrity.py")
        for integrity_evidence in (
            "validate_phase6_evaluation_bridge",
            "phase6_confirmation_boundary_purge_mismatch",
            "phase6_oos_model_output_or_return_mismatch",
            "phase6_trial_return_cell_mismatch",
        ):
            if integrity_evidence not in integrity:
                raise AssertionError(
                    "Phase 6 fail-closed bridge integrity evidence is missing: "
                    f"{integrity_evidence}"
                )

        leakage_contracts = normalized(
            ROOT / "services/backtester/src/fable5_backtester/contracts.py"
        )
        leakage_engine = normalized(ROOT / "services/backtester/src/fable5_backtester/leakage.py")
        for legacy_lineage_contract in (
            "PHASE5_SOURCE_FEATURE_DERIVATION_FORMULA",
            "source-decimal-times-frozen-multiplier-v1",
        ):
            if legacy_lineage_contract not in leakage_contracts:
                raise AssertionError(
                    "Phase 6 changed the legacy Phase 5 source-derivation contract: "
                    f"{legacy_lineage_contract}"
                )
        gate_root = ROOT / "services/backtester/src/fable5_backtester"
        for filename, expected_sha256 in PHASE_5_GATE_IMPLEMENTATION_SHA256.items():
            actual_sha256 = hashlib.sha256((gate_root / filename).read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise AssertionError(
                    "A Phase 5 gate implementation changed during Phase 6: "
                    f"{filename} ({actual_sha256})"
                )
        if enum_string_values(
            ROOT / "services/backtester/src/fable5_backtester/contracts.py",
            "LeakageCode",
        ) != {"L01", "L02", "L03", "L04", "L05", "L06"}:
            raise AssertionError("Phase 5 six-defect leakage vocabulary changed")
        for evidence_type in (
            "L01PriceBasisEvidence",
            "L02FundamentalRevisionEvidence",
            "L03FeatureAvailabilityEvidence",
            "L04DependencyScanEvidence",
            "L05MembershipReconstructionEvidence",
            "L06TrainOnlyFitEvidence",
        ):
            if evidence_type not in leakage_contracts or evidence_type not in leakage_engine:
                raise AssertionError(
                    f"Phase 6 changed or bypassed Phase 5 leakage evidence {evidence_type}"
                )

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        components = openapi["components"]["schemas"]
        expected_research_paths = {
            "/v1/research-runs": {"get", "post"},
            "/v1/research-runs/{run_id}": {"get"},
        }
        research_paths = {
            path: {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/research-runs")
        }
        if research_paths != expected_research_paths:
            raise AssertionError(f"Phase 6 research paths/methods are not exact: {research_paths}")
        for component in (
            "FamilyAEvidence",
            "FamilyBEvidence",
            "FamilyCEvidence",
            "Phase5EvaluationLink",
            "PreparedPipelineReproductionAudit",
            "PreparedRegimeEvidence",
            "ResearchBoundaryExclusion",
            "ResearchConfirmationInterval",
            "ResearchLedgerCell",
            "ResearchModelOutputSet",
            "ResearchTrialEconomics",
            "ResearchTrialSampleEconomics",
            "ResearchConfigurationId",
            "ResearchRunArtifact",
            "ResearchRunCreateRequest",
            "ResearchRunSummary",
            "StructuredTextFeatures",
            "TextFeatureExtraction",
            "ResearchTransformTrainingSample",
        ):
            if component not in components:
                raise AssertionError(f"Phase 6 OpenAPI is missing {component}")
        if set(components["ResearchConfigurationId"].get("enum", [])) != (
            PHASE_6_CONFIGURATION_IDS
        ):
            raise AssertionError("ResearchConfigurationId OpenAPI vocabulary is not exact")
        request_schema = components["ResearchRunCreateRequest"]
        request_fields = set(request_schema.get("properties", {}))
        expected_request_fields = {
            "mapping_id",
            "snapshot_ids",
            "research_configuration_id",
        }
        if (
            request_fields != expected_request_fields
            or set(request_schema.get("required", [])) != expected_request_fields
            or request_schema.get("additionalProperties") is not False
        ):
            raise AssertionError(
                "ResearchRunCreateRequest accepts client-authoritative results or metadata"
            )
        text_features = components["StructuredTextFeatures"]
        if set(text_features.get("properties", {})) != {
            "novelty",
            "direction",
            "uncertainty",
            "risk_change",
            "event_tags",
        }:
            raise AssertionError("LLM text output exceeds the structured-feature boundary")
        extraction = components["TextFeatureExtraction"]
        forbidden_extraction_fields = {
            "label",
            "signal",
            "model_decision",
            "buy_sell_call",
            "allocation",
            "position_size",
            "promotion_outcome",
            "execution_instruction",
        }
        if forbidden_extraction_fields & set(extraction.get("properties", {})):
            raise AssertionError("LLM extraction schema exposes a prohibited decision field")
        artifact_properties = components["ResearchRunArtifact"].get("properties", {})
        if (
            artifact_properties.get("synthetic", {}).get("const") is not True
            or artifact_properties.get("no_real_performance_claimed", {}).get("const") is not True
            or artifact_properties.get("pass_research_is_not_paper_approval", {}).get("const")
            is not True
            or artifact_properties.get("paper_approval_granted", {}).get("const") is not False
        ):
            raise AssertionError("Phase 6 research-only safety flags are not schema constants")

        domain_paths = {
            path: operations
            for path, operations in openapi["paths"].items()
            if path.startswith("/v1/")
        }
        for path, operations in domain_paths.items():
            methods = {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            if methods - {"get", "post"}:
                raise AssertionError(f"Phase 6 API exposes a mutation method: {path} {methods}")
        forbidden_phase7_paths = (
            "approval",
            "pre-order",
            "pre_order",
            "broker",
            "position",
            "order",
            "execution",
            "paper-trad",
            "live",
        )
        for path in domain_paths:
            if any(term in path.casefold() for term in forbidden_phase7_paths):
                raise AssertionError(f"Phase 7 or execution capability leaked into Phase 6: {path}")
        for surface in (
            contracts_path,
            research_root / "phase5.py",
            ROOT / "services/api/src/fable5_api/research.py",
            ROOT / "services/api/migrations/versions/0006_phase6_research.py",
        ):
            body = surface.read_text(encoding="utf-8")
            for forbidden_literal in (
                "APPROVED_PAPER",
                "PAPER_APPROVED",
                "LIVE_TRADING",
                "paper_execution",
                "live_execution",
            ):
                if forbidden_literal in body:
                    raise AssertionError(
                        "Phase 7 approval or execution state leaked into Phase 6: "
                        f"{surface.relative_to(ROOT)} {forbidden_literal}"
                    )

        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        for generated_contract in (
            "ResearchRunArtifact:",
            "ResearchRunCreateRequest:",
            "ResearchRunSummary:",
            "ResearchLedgerCell:",
            "ResearchModelOutputSet:",
            "TextFeatureExtraction:",
            '"/v1/research-runs"',
            '"/v1/research-runs/{run_id}"',
        ):
            if generated_contract not in generated:
                raise AssertionError(
                    f"Generated TypeScript Phase 6 contract is missing {generated_contract}"
                )

    print(f"Static repository policy checks passed for Phase {phase}.")


def run(
    command: list[str],
    *,
    project: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if project is not None:
        command = ["docker", "compose", "--project-name", project, *command]
    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT, check=True, text=True, env=env)


def acceptance_environment(phase: int = 1) -> tuple[dict[str, str], str, str]:
    sockets: list[socket.socket] = []
    try:
        for _ in range(4):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            sockets.append(listener)
        api_port, frontend_port, postgres_port, redis_port = (
            listener.getsockname()[1] for listener in sockets
        )
    finally:
        for listener in sockets:
            listener.close()

    api_url = f"http://127.0.0.1:{api_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    environment = os.environ.copy()
    environment.update(
        {
            "API_PORT": str(api_port),
            "FRONTEND_PORT": str(frontend_port),
            "POSTGRES_PORT": str(postgres_port),
            "REDIS_PORT": str(redis_port),
            "POSTGRES_DB": "fable5",
            "POSTGRES_USER": "fable5",
            "POSTGRES_PASSWORD": "fable5_dev_only",
            "FABLE5_ENVIRONMENT": "test",
            "FABLE5_VERIFY_PHASE": str(phase),
            "FABLE5_EXECUTION_MODE": "paper",
            "FABLE5_DATABASE_URL": (
                "postgresql+psycopg://fable5:fable5_dev_only@postgres:5432/fable5"
            ),
            "FABLE5_REDIS_URL": "redis://redis:6379/0",
            "FABLE5_CORS_ORIGINS": json.dumps(
                [
                    f"http://localhost:{frontend_port}",
                    frontend_url,
                ]
            ),
            "NEXT_PUBLIC_API_URL": api_url,
        }
    )
    if phase >= 5:
        git_sha = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
            raise RuntimeError(f"git rev-parse returned an invalid commit SHA: {git_sha!r}")
        environment["FABLE5_CODE_VERSION_GIT_SHA"] = git_sha
    return environment, api_url, frontend_url


def fetch_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"{url} returned {response.status}")
        if "application/json" not in response.headers.get("content-type", ""):
            raise AssertionError(f"{url} did not return JSON")
        return json.load(response)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    timeout_seconds: float = 10,
) -> dict[str, object] | list[object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status not in {200, 201, 202}:
            raise AssertionError(f"{method} {url} returned {response.status}")
        if "application/json" not in response.headers.get("content-type", ""):
            raise AssertionError(f"{method} {url} did not return JSON")
        return json.load(response)


def request_error_json(
    url: str,
    *,
    expected_status: int,
    method: str = "POST",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as exc:
        if exc.code != expected_status:
            raise AssertionError(
                f"{method} {url} returned {exc.code}, expected {expected_status}"
            ) from exc
        if "application/json" not in exc.headers.get("content-type", ""):
            raise AssertionError(f"{method} {url} error did not return JSON") from exc
        result = json.load(exc)
        if not isinstance(result, dict):
            raise AssertionError(f"{method} {url} error did not return an object") from exc
        return result
    raise AssertionError(f"{method} {url} unexpectedly succeeded")


def wait_for_cards(api_url: str, expected: int, timeout: int = 90) -> list[dict[str, object]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = request_json(f"{api_url}/v1/cards")
        if isinstance(result, list) and len(result) >= expected:
            return [item for item in result if isinstance(item, dict)]
        time.sleep(1)
    raise AssertionError(f"Timed out waiting for {expected} Phase 2 cards")


def wait_for_source_cards(
    api_url: str, source_version_ids: set[str], timeout: int = 90
) -> dict[str, dict[str, object]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = request_json(f"{api_url}/v1/cards")
        if isinstance(result, list):
            cards = {
                str(card["source_version_id"]): card
                for card in result
                if isinstance(card, dict) and "source_version_id" in card
            }
            if source_version_ids <= set(cards):
                return {version_id: cards[version_id] for version_id in source_version_ids}
        time.sleep(1)
    raise AssertionError(
        "Timed out waiting for Phase 3 fixture cards: " + ", ".join(sorted(source_version_ids))
    )


def verify_phase2_api(api_url: str) -> dict[str, str]:
    official = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "official",
            "authority_verification_method": "synthetic_fixture",
            "raw_text": "Official issuer release supplied as synthetic source evidence.",
            "ingest_idempotency_key": "acceptance-official-v1",
        },
    )
    if not isinstance(official, dict):
        raise AssertionError("Unexpected official source response")
    official_version = str(official["source_version"]["source_version_id"])

    linked_social = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "social",
            "raw_text": (
                "If Reddit attention changes around an issuer event, the source makes a next day "
                "stock claim."
            ),
            "official_corroboration_source_version_ids": [official_version],
            "ingest_idempotency_key": "acceptance-social-linked-v1",
        },
    )
    unlinked_social = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "social",
            "raw_text": "If social attention changes, the source makes a next day stock claim.",
            "ingest_idempotency_key": "acceptance-social-unlinked-v1",
        },
    )
    hft = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "other",
            "raw_text": (
                "When full-depth order-book state changes in milliseconds, the source describes "
                "a sub-second scalp."
            ),
            "ingest_idempotency_key": "acceptance-hft-v1",
        },
    )
    for response in (linked_social, unlinked_social, hft):
        if not isinstance(response, dict) or response.get("extraction") is None:
            raise AssertionError("Text intake did not create an extraction request")

    cards = wait_for_cards(api_url, expected=4)
    by_version = {str(card["source_version_id"]): card for card in cards}
    linked_version = str(linked_social["source_version"]["source_version_id"])
    unlinked_version = str(unlinked_social["source_version"]["source_version_id"])
    hft_version = str(hft["source_version"]["source_version_id"])
    linked_card = by_version[linked_version]
    unlinked_card = by_version[unlinked_version]
    hft_card = by_version[hft_version]
    if linked_card["corroboration_status"] != "verified":
        raise AssertionError("Exact verified official source did not corroborate social intake")
    if linked_card["contribution_status"] != "not_blocked_by_corroboration":
        raise AssertionError("Verified social corroboration did not clear its narrow intake gate")
    if unlinked_card["contribution_status"] != "blocked_official_corroboration_required":
        raise AssertionError("Uncorroborated social intake was not blocked")
    if "social_manipulation_risk" not in unlinked_card["ambiguity_flags"]:
        raise AssertionError("Social manipulation risk was not preserved")
    if hft_card["infra_risk"] != "high":
        raise AssertionError("Order-book/sub-second fixture was not high infrastructure risk")
    if set(hft_card["action_rule"]) != {"state", "claim_ids"}:
        raise AssertionError("Action rule exposed something beyond source-evidence references")

    card_detail = request_json(f"{api_url}/v1/cards/{linked_card['card_id']}")
    if not isinstance(card_detail, dict):
        raise AssertionError("Card detail response was not an object")
    memo = card_detail["memo"]
    if "not investment advice" not in memo["markdown"]:
        raise AssertionError("Research memo is missing the advice boundary")

    repeated = request_json(
        f"{api_url}/v1/source-versions/{linked_version}/extractions",
        method="POST",
    )
    if (
        not isinstance(repeated, dict)
        or repeated["extraction_request_id"]
        != (linked_social["extraction"]["extraction_request_id"])
    ):
        raise AssertionError("Identical extraction retry did not reuse its immutable request")

    correction = request_json(
        f"{api_url}/v1/sources/{hft['source']['source_id']}/versions",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "other",
            "raw_text": (
                "Corrected source text: when order-book state changes in milliseconds, "
                "it describes a sub-second scalp."
            ),
            "ingest_idempotency_key": "acceptance-hft-v2",
        },
    )
    if not isinstance(correction, dict):
        raise AssertionError("Unexpected correction response")
    if correction["source_version"]["source_version"] != 2:
        raise AssertionError("Source correction did not append version 2")
    if correction["source_version"]["parent_source_version_id"] != hft_version:
        raise AssertionError("Source correction did not preserve its exact parent")
    correction_version = str(correction["source_version"]["source_version_id"])
    corrected_cards = wait_for_cards(api_url, expected=5)
    if correction_version not in {str(card["source_version_id"]) for card in corrected_cards}:
        raise AssertionError("Correction extraction did not finish through the research queue")

    extractions_before_url = request_json(f"{api_url}/v1/extractions")
    if not isinstance(extractions_before_url, list):
        raise AssertionError("Extraction list response was not an array")
    url_only = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "url_provenance",
            "source_authority": "unknown",
            "source_url": "https://example.invalid/not-retrieved",
            "ingest_idempotency_key": "acceptance-url-only-v1",
        },
    )
    if not isinstance(url_only, dict) or url_only["extraction"] is not None:
        raise AssertionError("URL-only provenance unexpectedly triggered retrieval/extraction")
    extractions_after_url = request_json(f"{api_url}/v1/extractions")
    if not isinstance(extractions_after_url, list) or len(extractions_after_url) != len(
        extractions_before_url
    ):
        raise AssertionError("URL-only intake created an extraction request")
    url_version = str(url_only["source_version"]["source_version_id"])
    try:
        request_json(
            f"{api_url}/v1/source-versions/{url_version}/extractions",
            method="POST",
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 422:
            raise AssertionError(
                f"URL-only extraction failed with HTTP {exc.code}, not 422"
            ) from exc
    else:
        raise AssertionError("Explicit URL-only extraction unexpectedly succeeded")
    final_extractions = request_json(f"{api_url}/v1/extractions")
    if not isinstance(final_extractions, list) or len(final_extractions) != len(
        extractions_before_url
    ):
        raise AssertionError("Explicit URL-only extraction created a request or queue job")

    linked_extraction = linked_social["extraction"]
    return {
        "request_id": str(linked_extraction["extraction_request_id"]),
        "rq_job_id": str(linked_extraction["rq_job_id"]),
    }


def verify_phase3_api(api_url: str) -> str:
    cards_before = request_json(f"{api_url}/v1/cards")
    if not isinstance(cards_before, list):
        raise AssertionError("Phase 2 card list was not available before Phase 3 mapping")
    openapi_before = request_json(f"{api_url}/openapi.json")
    if not isinstance(openapi_before, dict) or not isinstance(openapi_before.get("paths"), dict):
        raise AssertionError("Live OpenAPI was unavailable before Phase 3 mapping")
    paths_before = set(openapi_before["paths"])

    fixture_root = ROOT / "services" / "extraction" / "tests" / "fixtures"
    versions_by_fixture: dict[str, str] = {}
    for filename in PHASE_2_FIXTURES:
        fixture = json.loads((fixture_root / filename).read_text(encoding="utf-8"))
        created = request_json(
            f"{api_url}/v1/sources",
            method="POST",
            payload={
                "source_type": "synthetic_fixture",
                "source_authority": fixture["source_authority"],
                "raw_text": fixture["raw_text"],
                "ingest_idempotency_key": f"phase3-{fixture['fixture_id']}-v1",
            },
        )
        if not isinstance(created, dict) or created.get("extraction") is None:
            raise AssertionError(f"Phase 3 fixture {filename} did not create an extraction")
        versions_by_fixture[filename] = str(created["source_version"]["source_version_id"])

    cards_by_version = wait_for_source_cards(api_url, set(versions_by_fixture.values()))
    ranking_card = cards_by_version[versions_by_fixture["ranking.json"]]
    concurrent_start = Barrier(2)

    def create_ranking_mapping() -> dict[str, object]:
        concurrent_start.wait(timeout=10)
        result = request_json(
            f"{api_url}/v1/cards/{ranking_card['card_id']}/mappings",
            method="POST",
        )
        if not isinstance(result, dict):
            raise AssertionError("Concurrent Phase 3 mapping returned no object")
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent_results = list(executor.map(lambda _: create_ranking_mapping(), range(2)))
    if concurrent_results[0] != concurrent_results[1]:
        raise AssertionError("Concurrent identical Phase 3 mappings were not idempotent")
    concurrent_list = request_json(f"{api_url}/v1/mappings?card_id={ranking_card['card_id']}")
    if not isinstance(concurrent_list, list) or len(concurrent_list) != 1:
        raise AssertionError("Concurrent identical mapping requests persisted more than one row")

    mapped_by_fixture: dict[str, dict[str, object]] = {}
    for filename, (family, verdict, expected_reasons) in PHASE_3_FIXTURE_MATRIX.items():
        card = cards_by_version[versions_by_fixture[filename]]
        result = (
            concurrent_results[0]
            if filename == "ranking.json"
            else request_json(
                f"{api_url}/v1/cards/{card['card_id']}/mappings",
                method="POST",
            )
        )
        if not isinstance(result, dict) or not isinstance(result.get("mapping"), dict):
            raise AssertionError(f"Phase 3 fixture {filename} returned no mapping object")
        if not isinstance(result.get("rationale"), dict):
            raise AssertionError(f"Phase 3 fixture {filename} returned no rationale object")
        mapping = result["mapping"]
        rationale = result["rationale"]
        if mapping.get("card_id") != card["card_id"]:
            raise AssertionError(f"Phase 3 fixture {filename} lost its card lineage")
        if mapping.get("source_version_id") != card["source_version_id"]:
            raise AssertionError(f"Phase 3 fixture {filename} lost its source-version lineage")
        if mapping.get("mapper_rule_set_sha256") != PHASE_3_RULE_SET_SHA256:
            raise AssertionError(f"Phase 3 fixture {filename} used an unexpected rule-set hash")
        actual = (mapping.get("canonical_family"), mapping.get("verdict"))
        if actual != (family, verdict):
            raise AssertionError(
                f"Phase 3 fixture {filename} mapped to {actual}, expected {(family, verdict)}"
            )
        reasons = mapping.get("reason_codes")
        if not isinstance(reasons, list) or not reasons:
            raise AssertionError(f"Phase 3 fixture {filename} has no ordered reason codes")
        if expected_reasons is not None and reasons != expected_reasons:
            raise AssertionError(
                f"Phase 3 fixture {filename} reasons {reasons} != {expected_reasons}"
            )
        rule_ids = mapping.get("matched_rule_ids")
        if not isinstance(rule_ids, list) or not rule_ids:
            raise AssertionError(f"Phase 3 fixture {filename} has no matched rule IDs")
        if rationale.get("mapping_id") != mapping.get("mapping_id"):
            raise AssertionError(f"Phase 3 fixture {filename} rationale lost mapping lineage")
        if not isinstance(rationale.get("markdown"), str) or not rationale["markdown"]:
            raise AssertionError(f"Phase 3 fixture {filename} rationale is empty")
        mapped_by_fixture[filename] = result

    first = mapped_by_fixture["ranking.json"]
    first_mapping = first["mapping"]
    repeated = request_json(
        f"{api_url}/v1/cards/{first_mapping['card_id']}/mappings",
        method="POST",
    )
    if not isinstance(repeated, dict):
        raise AssertionError("Idempotent Phase 3 mapping retry returned no object")
    if repeated.get("mapping") != first_mapping or repeated.get("rationale") != first["rationale"]:
        raise AssertionError("Identical card/rule-set mapping retry was not idempotent")

    detail = request_json(f"{api_url}/v1/mappings/{first_mapping['mapping_id']}")
    if detail != first:
        raise AssertionError("Phase 3 mapping detail did not reproduce the persisted artifact")
    listed = request_json(f"{api_url}/v1/mappings")
    if not isinstance(listed, list) or first_mapping["mapping_id"] not in {
        item.get("mapping", {}).get("mapping_id")
        for item in listed
        if isinstance(item, dict) and isinstance(item.get("mapping"), dict)
    }:
        raise AssertionError("Phase 3 mapping list omitted a persisted mapping")

    verified_social = next(
        (
            card
            for card in cards_before
            if isinstance(card, dict)
            and isinstance(card.get("signal_family"), dict)
            and card["signal_family"].get("value") == "social_or_news_claim"
            and card.get("corroboration_status") == "verified"
        ),
        None,
    )
    if verified_social is None:
        raise AssertionError("Phase 2 acceptance data contained no verified social card")
    verified_mapping = request_json(
        f"{api_url}/v1/cards/{verified_social['card_id']}/mappings",
        method="POST",
    )
    if (
        not isinstance(verified_mapping, dict)
        or not isinstance(verified_mapping.get("mapping"), dict)
        or verified_mapping["mapping"].get("canonical_family") != "C_OFFICIAL_EVENT_TEXT_OVERLAY"
        or verified_mapping["mapping"].get("verdict") != "BUILD_RESEARCH"
    ):
        raise AssertionError("Verified social evidence did not map to the eligible C overlay")

    live_openapi = request_json(f"{api_url}/openapi.json")
    if not isinstance(live_openapi, dict) or not isinstance(live_openapi.get("paths"), dict):
        raise AssertionError("Live OpenAPI was unavailable after HFT rejection mapping")
    if set(live_openapi["paths"]) != paths_before:
        raise AssertionError("HFT rejection mapping changed the API surface or created a scaffold")
    rendered_paths = " ".join(live_openapi["paths"]).lower()
    for forbidden in ("signal", "strategy", "backtest", "broker", "position", "order", "live"):
        if forbidden in rendered_paths:
            raise AssertionError(
                f"HFT mapping exposed a forbidden downstream API path: {forbidden}"
            )

    print("Phase 3 six-fixture mapping matrix and concurrent idempotency proof passed.")
    return str(ranking_card["card_id"])


def verify_phase4_api(api_url: str) -> str:
    family_b_source = request_json(
        f"{api_url}/v1/sources",
        method="POST",
        payload={
            "source_type": "synthetic_fixture",
            "source_authority": "other",
            "raw_text": (
                "When the moving average crosses, evaluate the next day trend claim in liquid ETFs."
            ),
            "ingest_idempotency_key": "phase4-family-b-verifier-v1",
        },
    )
    if not isinstance(family_b_source, dict) or not isinstance(
        family_b_source.get("source_version"), dict
    ):
        raise AssertionError("Phase 4 verifier could not create a testable Family B source")
    family_b_source_version_id = str(family_b_source["source_version"]["source_version_id"])
    family_b_card = wait_for_source_cards(api_url, {family_b_source_version_id})[
        family_b_source_version_id
    ]
    family_b_result = request_json(
        f"{api_url}/v1/cards/{family_b_card['card_id']}/mappings",
        method="POST",
    )
    if (
        not isinstance(family_b_result, dict)
        or not isinstance(family_b_result.get("mapping"), dict)
        or family_b_result["mapping"].get("canonical_family") != "B_TIME_SERIES_MOMENTUM_REGIME"
        or family_b_result["mapping"].get("verdict") != "BUILD_RESEARCH"
    ):
        raise AssertionError("Phase 4 verifier did not produce an authorized Family B mapping")

    mappings = request_json(f"{api_url}/v1/mappings")
    if not isinstance(mappings, list):
        raise AssertionError("Phase 3 mappings were unavailable before Phase 4 snapshot creation")

    authorized_mappings: dict[str, dict[str, object]] = {}
    unauthorized_mapping: dict[str, object] | None = None
    for item in mappings:
        if not isinstance(item, dict) or not isinstance(item.get("mapping"), dict):
            continue
        mapping = item["mapping"]
        family = mapping.get("canonical_family")
        if mapping.get("verdict") == "BUILD_RESEARCH" and isinstance(family, str):
            authorized_mappings[family] = mapping
        elif mapping.get("verdict") != "BUILD_RESEARCH":
            unauthorized_mapping = mapping
    family_capabilities = {
        "A_CROSS_SECTIONAL_EQUITY_RANKING": "ohlcv",
        "B_TIME_SERIES_MOMENTUM_REGIME": "trading_calendar",
        "C_OFFICIAL_EVENT_TEXT_OVERLAY": "official_document_event_metadata",
    }
    missing_families = set(family_capabilities) - set(authorized_mappings)
    if missing_families or unauthorized_mapping is None:
        raise AssertionError(
            "Phase 4 verifier could not resolve authorized A/B/C and denied mappings: "
            f"{sorted(missing_families)}"
        )

    as_of_text = "2024-01-03T00:00:00Z"
    as_of_utc = datetime.fromisoformat(as_of_text.replace("Z", "+00:00"))
    created_by_family: dict[str, dict[str, object]] = {}
    payload_by_family: dict[str, dict[str, object]] = {}
    for family, capability in family_capabilities.items():
        mapping = authorized_mappings[family]
        create_payload: dict[str, object] = {
            "mapping_id": mapping["mapping_id"],
            "as_of_utc": as_of_text,
            "capability": capability,
            "mock_configuration_id": "phase4-synthetic-default-v1",
        }
        created = request_json(
            f"{api_url}/v1/data-snapshots",
            method="POST",
            payload=create_payload,
        )
        repeated = request_json(
            f"{api_url}/v1/data-snapshots",
            method="POST",
            payload=create_payload,
        )
        if not isinstance(created, dict) or created != repeated:
            raise AssertionError(
                f"Identical Phase 4 {family} API creation was not deterministic and idempotent"
            )
        snapshot = created.get("snapshot")
        constituents = created.get("constituents")
        if not isinstance(snapshot, dict) or not isinstance(constituents, list) or not constituents:
            raise AssertionError(f"Phase 4 {family} API returned no immutable constituents")
        snapshot_id = snapshot.get("snapshot_id")
        snapshot_sha256 = snapshot.get("snapshot_sha256")
        if not isinstance(snapshot_id, str) or not isinstance(snapshot_sha256, str):
            raise AssertionError(f"Phase 4 {family} API omitted snapshot identity/hash")
        if not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256):
            raise AssertionError(f"Phase 4 {family} API returned a non-SHA-256 snapshot hash")
        manifest = snapshot.get("manifest")
        if (
            not isinstance(manifest, dict)
            or not isinstance(manifest.get("payload"), dict)
            or not isinstance(manifest["payload"].get("mapping"), dict)
            or manifest["payload"]["mapping"].get("canonical_family") != family
        ):
            raise AssertionError(f"Phase 4 {family} manifest lost persisted mapping lineage")
        for constituent in constituents:
            if not isinstance(constituent, dict):
                raise AssertionError("Phase 4 snapshot constituent was not an object")
            if constituent.get("snapshot_id") != snapshot_id:
                raise AssertionError("Phase 4 snapshot constituent lost its snapshot lineage")
            available_at = constituent.get("available_at")
            if not isinstance(available_at, str):
                raise AssertionError("Phase 4 snapshot constituent omitted available_at")
            parsed_available_at = datetime.fromisoformat(available_at.replace("Z", "+00:00"))
            if parsed_available_at > as_of_utc:
                raise AssertionError("Phase 4 API included a future-available constituent")

        detail = request_json(f"{api_url}/v1/data-snapshots/{snapshot_id}")
        if detail != created:
            raise AssertionError(f"Phase 4 {family} detail did not reproduce its bundle")
        listed = request_json(
            f"{api_url}/v1/data-snapshots?mapping_id={mapping['mapping_id']}&limit=100"
        )
        if not isinstance(listed, list) or snapshot_id not in {
            item.get("snapshot_id") for item in listed if isinstance(item, dict)
        }:
            raise AssertionError(f"Phase 4 {family} list omitted its persisted snapshot")
        created_by_family[family] = created
        payload_by_family[family] = create_payload

    family_a = "A_CROSS_SECTIONAL_EQUITY_RANKING"
    create_payload = payload_by_family[family_a]
    created = created_by_family[family_a]
    snapshot = created["snapshot"]
    assert isinstance(snapshot, dict)
    snapshot_id = snapshot["snapshot_id"]
    assert isinstance(snapshot_id, str)

    forbidden_client_payload = dict(create_payload)
    forbidden_client_payload.update(
        {
            "canonical_family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
            "observations": [],
            "provider_id": "client-claim",
            "snapshot_sha256": "0" * 64,
        }
    )
    request_error_json(
        f"{api_url}/v1/data-snapshots",
        expected_status=422,
        payload=forbidden_client_payload,
    )
    denied_payload = dict(create_payload)
    denied_payload["mapping_id"] = unauthorized_mapping["mapping_id"]
    request_error_json(
        f"{api_url}/v1/data-snapshots",
        expected_status=422,
        payload=denied_payload,
    )
    unavailable_payload = dict(create_payload)
    unavailable_payload["mock_configuration_id"] = "unregistered-configuration"
    unavailable = request_error_json(
        f"{api_url}/v1/data-snapshots",
        expected_status=503,
        payload=unavailable_payload,
    )
    if (
        unavailable.get("status") != "unavailable"
        or unavailable.get("reason_code") != "configuration_unavailable"
        or "detail" in unavailable
    ):
        raise AssertionError("Phase 4 API did not return its typed sanitized unavailable result")
    request_error_json(
        f"{api_url}/v1/data-snapshots",
        expected_status=422,
        payload={**create_payload, "capability": "options"},
    )

    print(
        "Phase 4 authorized A/B/C create/read/list, deterministic retry, server-authority, and "
        f"fail-closed API proof passed (Family A snapshot {snapshot_id})."
    )
    return snapshot_id


def verify_phase5_api(api_url: str, phase4_snapshot_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f-]{36}", phase4_snapshot_id):
        raise AssertionError("Phase 5 did not receive a valid preserved Phase 4 snapshot identity")
    preserved_ohlcv = request_json(f"{api_url}/v1/data-snapshots/{phase4_snapshot_id}")
    if not isinstance(preserved_ohlcv, dict) or not isinstance(
        preserved_ohlcv.get("snapshot"), dict
    ):
        raise AssertionError("Phase 5 could not reload the preserved Phase 4 OHLCV snapshot")
    preserved_snapshot = preserved_ohlcv["snapshot"]
    manifest = preserved_snapshot.get("manifest")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("payload"), dict):
        raise AssertionError("Preserved Phase 4 OHLCV snapshot omitted its immutable manifest")
    manifest_payload = manifest["payload"]
    mapping = manifest_payload.get("mapping")
    snapshot_request = manifest_payload.get("request")
    if not isinstance(mapping, dict) or not isinstance(snapshot_request, dict):
        raise AssertionError("Preserved Phase 4 OHLCV snapshot lost request/mapping lineage")
    if (
        mapping.get("canonical_family") != "A_CROSS_SECTIONAL_EQUITY_RANKING"
        or mapping.get("verdict") != "BUILD_RESEARCH"
        or snapshot_request.get("capability") != "ohlcv"
        or preserved_snapshot.get("snapshot_id") != phase4_snapshot_id
    ):
        raise AssertionError("Phase 5 did not reuse the authorized Family A OHLCV snapshot")
    mapping_id = mapping.get("mapping_id")
    as_of_text = snapshot_request.get("as_of_utc")
    if not isinstance(mapping_id, str) or not isinstance(as_of_text, str):
        raise AssertionError("Preserved Family A snapshot omitted mapping/as-of identity")

    membership_created = request_json(
        f"{api_url}/v1/data-snapshots",
        method="POST",
        payload={
            "mapping_id": mapping_id,
            "as_of_utc": as_of_text,
            "capability": "universe_membership",
            "mock_configuration_id": "phase4-synthetic-default-v1",
        },
    )
    if not isinstance(membership_created, dict) or not isinstance(
        membership_created.get("snapshot"), dict
    ):
        raise AssertionError("Phase 5 could not resolve an immutable membership snapshot")
    membership_snapshot = membership_created["snapshot"]
    membership_snapshot_id = membership_snapshot.get("snapshot_id")
    membership_manifest = membership_snapshot.get("manifest")
    if not isinstance(membership_snapshot_id, str) or not isinstance(membership_manifest, dict):
        raise AssertionError("Phase 5 membership snapshot omitted its identity/manifest")
    membership_manifest_payload = membership_manifest.get("payload")
    if not isinstance(membership_manifest_payload, dict) or not isinstance(
        membership_manifest_payload.get("request"), dict
    ):
        raise AssertionError("Phase 5 membership snapshot lost request lineage")
    membership_request = membership_manifest_payload["request"]
    if (
        membership_manifest_payload.get("mapping") != mapping
        or membership_request.get("mapping") != mapping
        or membership_request.get("as_of_utc") != as_of_text
        or membership_request.get("capability") != "universe_membership"
        or membership_snapshot_id == phase4_snapshot_id
    ):
        raise AssertionError("Phase 5 membership snapshot did not preserve mapping/as-of lineage")

    policy_request = {
        "policy_id": "b4e2146e-f1da-5c15-ada2-01bfd61ead9e",
        "policy_version": 1,
    }
    policy = request_json(
        f"{api_url}/v1/evaluation-policies",
        method="POST",
        payload=policy_request,
    )
    repeated_policy = request_json(
        f"{api_url}/v1/evaluation-policies",
        method="POST",
        payload=policy_request,
    )
    if not isinstance(policy, dict) or policy != repeated_policy:
        raise AssertionError("Frozen Phase 5 policy creation was not deterministic/idempotent")
    policy_hash = policy.get("policy_sha256")
    if not isinstance(policy_hash, str) or re.fullmatch(r"[0-9a-f]{64}", policy_hash) is None:
        raise AssertionError("Frozen Phase 5 policy omitted its canonical SHA-256")
    if policy.get("synthetic_fixture_policy") is not True:
        raise AssertionError("Phase 5 registered a policy outside its synthetic fixture boundary")
    if policy.get("strategy_family") != "A_CROSS_SECTIONAL_EQUITY_RANKING" or policy.get(
        "required_snapshot_capabilities"
    ) != ["ohlcv", "universe_membership"]:
        raise AssertionError(
            "Phase 5 registered policy lost its exact Family A two-capability contract"
        )
    policy_detail = request_json(
        f"{api_url}/v1/evaluation-policies/{policy_request['policy_id']}/versions/1"
    )
    policies = request_json(f"{api_url}/v1/evaluation-policies?limit=100")
    if policy_detail != policy or not isinstance(policies, list) or policy not in policies:
        raise AssertionError("Phase 5 policy create/read/list contract is incomplete")

    run_request = {
        **policy_request,
        "mapping_id": mapping_id,
        "snapshot_ids": [phase4_snapshot_id, membership_snapshot_id],
        "fixture_id": "phase5-deterministic-research-ledger-v1",
    }
    report = request_json(
        f"{api_url}/v1/evaluation-reports",
        method="POST",
        payload=run_request,
    )
    repeated_report = request_json(
        f"{api_url}/v1/evaluation-reports",
        method="POST",
        payload=run_request,
    )
    if not isinstance(report, dict) or report != repeated_report:
        raise AssertionError("Phase 5 identical run creation was not deterministic/idempotent")
    artifact_id = report.get("artifact_id")
    artifact_hash = report.get("artifact_sha256")
    if not isinstance(artifact_id, str) or not isinstance(artifact_hash, str):
        raise AssertionError("Phase 5 report omitted its immutable identity/hash")
    if re.fullmatch(r"[0-9a-f]{64}", artifact_hash) is None:
        raise AssertionError("Phase 5 report returned an invalid artifact SHA-256")
    if (
        report.get("promotion_state") != "PASS_RESEARCH"
        or report.get("synthetic") is not True
        or report.get("no_real_performance_claimed") is not True
        or report.get("pass_research_is_not_paper_approval") is not True
    ):
        raise AssertionError("Phase 5 report violated its synthetic research-only state boundary")
    if report.get("evaluation_policy_sha256") != policy_hash:
        raise AssertionError("Phase 5 report lost its frozen policy hash")
    if report.get("mapping_id") != mapping_id or report.get("raw_trial_count") != 6:
        raise AssertionError("Phase 5 report lost mapping or complete trial-count lineage")
    data_snapshots = report.get("data_snapshots")
    if not isinstance(data_snapshots, list) or len(data_snapshots) != 2:
        raise AssertionError("Phase 5 report omitted immutable snapshot evidence")
    snapshots_by_capability = {
        item.get("capability"): item for item in data_snapshots if isinstance(item, dict)
    }
    if (
        set(snapshots_by_capability) != {"ohlcv", "universe_membership"}
        or snapshots_by_capability["ohlcv"].get("snapshot_id") != phase4_snapshot_id
        or snapshots_by_capability["universe_membership"].get("snapshot_id")
        != membership_snapshot_id
        or any(item.get("as_of_utc") != as_of_text for item in snapshots_by_capability.values())
    ):
        raise AssertionError("Phase 5 report did not bind both exact Family A snapshots")

    source_observations = report.get("source_observations")
    sample_lineage = report.get("sample_lineage")
    sample_lineage_sha256 = report.get("sample_lineage_sha256")
    if (
        not isinstance(source_observations, list)
        or len(source_observations) != 2
        or not isinstance(sample_lineage, list)
        or len(sample_lineage) != 20
        or not isinstance(sample_lineage_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", sample_lineage_sha256) is None
    ):
        raise AssertionError("Phase 5 report omitted exact Phase 4 source/sample lineage")
    sources_by_capability = {
        item.get("key", {}).get("capability"): item
        for item in source_observations
        if isinstance(item, dict) and isinstance(item.get("key"), dict)
    }
    if set(sources_by_capability) != {"ohlcv", "universe_membership"}:
        raise AssertionError("Phase 5 source lineage omitted a required capability")
    source_ref_fields = (
        "capability",
        "snapshot_id",
        "snapshot_sha256",
        "raw_observation_id",
        "observation_revision_id",
        "normalized_observation_id",
        "raw_payload_sha256",
        "normalized_content_sha256",
    )
    source_timing_by_ref: dict[tuple[object, ...], tuple[datetime, datetime]] = {}
    for capability, resolved_source in sources_by_capability.items():
        normalized_source = resolved_source.get("normalized_observation")
        if not isinstance(normalized_source, dict):
            raise AssertionError("Phase 5 source lineage omitted normalized source evidence")
        source_ref = {
            "capability": capability,
            "snapshot_id": normalized_source.get("snapshot_id"),
            "snapshot_sha256": normalized_source.get("snapshot_sha256"),
            "raw_observation_id": normalized_source.get("raw_observation_id"),
            "observation_revision_id": normalized_source.get("observation_revision_id"),
            "normalized_observation_id": normalized_source.get("normalized_observation_id"),
            "raw_payload_sha256": normalized_source.get("raw_payload_sha256"),
            "normalized_content_sha256": normalized_source.get("normalized_content_sha256"),
        }
        source_event_text = normalized_source.get("event_time")
        source_available_text = normalized_source.get("available_at")
        if (
            any(value is None for value in source_ref.values())
            or not isinstance(source_event_text, str)
            or not isinstance(source_available_text, str)
        ):
            raise AssertionError("Phase 5 source lineage omitted exact PIT reference fields")
        source_ref_key = tuple(source_ref[field] for field in source_ref_fields)
        if source_ref_key in source_timing_by_ref:
            raise AssertionError("Phase 5 source lineage contains an ambiguous exact reference")
        source_timing_by_ref[source_ref_key] = (
            datetime.fromisoformat(source_event_text.replace("Z", "+00:00")),
            datetime.fromisoformat(source_available_text.replace("Z", "+00:00")),
        )
    resolved_ohlcv_source = sources_by_capability["ohlcv"]
    normalized_ohlcv = resolved_ohlcv_source.get("normalized_observation")
    if (
        not isinstance(normalized_ohlcv, dict)
        or normalized_ohlcv.get("snapshot_id") != phase4_snapshot_id
        or resolved_ohlcv_source.get("disposition") != "included_as_of"
        or not isinstance(normalized_ohlcv.get("payload"), dict)
    ):
        raise AssertionError("Phase 5 OHLCV evidence is not bound to the preserved snapshot row")
    expected_membership_observation_id = "62b27683-7bac-5713-81db-6ea3a0aeb40e"
    expected_membership_key = {
        "capability": "universe_membership",
        "normalized_observation_id": expected_membership_observation_id,
    }
    resolved_membership_source = sources_by_capability["universe_membership"]
    normalized_membership = resolved_membership_source.get("normalized_observation")
    if not isinstance(normalized_membership, dict):
        raise AssertionError("Phase 5 membership source lineage is not structured evidence")
    if (
        resolved_membership_source.get("key") != expected_membership_key
        or resolved_membership_source.get("disposition") != "included_as_of"
        or normalized_membership.get("snapshot_id") != membership_snapshot_id
        or normalized_membership.get("normalized_observation_id")
        != expected_membership_observation_id
        or normalized_membership.get("source_record_id") != "synthetic-membership-2019"
        or normalized_membership.get("instrument_id") != "11111111-1111-5111-8111-111111111111"
        or normalized_membership.get("listing_id") != "22222222-2222-5222-8222-222222222222"
        or normalized_membership.get("payload")
        != {
            "record_type": "universe_membership",
            "universe_id": "synthetic-us-equity",
            "status": "included",
        }
    ):
        raise AssertionError("Phase 5 membership status or immutable identity drifted")
    expected_membership_ref = {
        "capability": "universe_membership",
        "snapshot_id": membership_snapshot_id,
        "snapshot_sha256": normalized_membership.get("snapshot_sha256"),
        "raw_observation_id": normalized_membership.get("raw_observation_id"),
        "observation_revision_id": normalized_membership.get("observation_revision_id"),
        "normalized_observation_id": expected_membership_observation_id,
        "raw_payload_sha256": normalized_membership.get("raw_payload_sha256"),
        "normalized_content_sha256": normalized_membership.get("normalized_content_sha256"),
    }
    if any(value is None for value in expected_membership_ref.values()):
        raise AssertionError("Phase 5 membership source omitted immutable reference fields")
    membership_event = normalized_membership.get("event_time")
    membership_available = normalized_membership.get("available_at")
    membership_valid_from = normalized_membership.get("valid_from")
    membership_valid_to = normalized_membership.get("valid_to")
    if (
        membership_event != "2019-01-01T00:00:00Z"
        or membership_available != "2019-01-02T05:00:00Z"
        or membership_valid_from != "2019-01-01T00:00:00Z"
        or membership_valid_to != "2022-01-01T00:00:00Z"
    ):
        raise AssertionError("Phase 5 membership PIT interval drifted from frozen evidence")
    membership_event_utc = datetime.fromisoformat(membership_event.replace("Z", "+00:00"))
    membership_available_utc = datetime.fromisoformat(membership_available.replace("Z", "+00:00"))
    membership_valid_from_utc = datetime.fromisoformat(membership_valid_from.replace("Z", "+00:00"))
    membership_valid_to_utc = datetime.fromisoformat(membership_valid_to.replace("Z", "+00:00"))
    lineage_by_sample = {
        item.get("sample_id"): item for item in sample_lineage if isinstance(item, dict)
    }
    if len(lineage_by_sample) != len(sample_lineage) or any(
        not isinstance(item.get("sample_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", item["sample_sha256"]) is None
        or not isinstance(item.get("source_observation_refs"), list)
        or len(item["source_observation_refs"]) != 2
        or not isinstance(item.get("feature_available_at_utc"), str)
        or {ref.get("capability") for ref in item["source_observation_refs"]}
        != {"ohlcv", "universe_membership"}
        or item.get("membership_source_observation_key") != expected_membership_key
        or not isinstance(item.get("feature_derivation"), dict)
        or item["feature_derivation"].get("formula_id")
        != "source-decimal-times-frozen-multiplier-v1"
        or not isinstance(item["feature_derivation"].get("derived_feature_value"), str)
        or item.get("synthetic_ledger_value_rule")
        != "deterministic-synthetic-research-ledger-input-v1"
        for item in lineage_by_sample.values()
    ):
        raise AssertionError(
            "Phase 5 sample lineage is incomplete, non-unique, or not source-derived"
        )
    for lineage in lineage_by_sample.values():
        decision_text = lineage.get("decision_time_utc")
        feature_available_text = lineage.get("feature_available_at_utc")
        if not isinstance(decision_text, str) or not isinstance(feature_available_text, str):
            raise AssertionError("Phase 5 sample lineage omitted its information interval")
        decision_time_utc = datetime.fromisoformat(decision_text.replace("Z", "+00:00"))
        feature_available_at_utc = datetime.fromisoformat(
            feature_available_text.replace("Z", "+00:00")
        )
        if feature_available_at_utc > decision_time_utc:
            raise AssertionError("Phase 5 feature availability follows its decision time")
        for source_ref in lineage["source_observation_refs"]:
            source_ref_key = tuple(source_ref.get(field) for field in source_ref_fields)
            source_timing = source_timing_by_ref.get(source_ref_key)
            if source_timing is None:
                raise AssertionError(
                    "Phase 5 sample references unknown or mismatched source evidence"
                )
            source_event_utc, source_available_utc = source_timing
            if (
                source_event_utc > feature_available_at_utc
                or source_available_utc > feature_available_at_utc
            ):
                raise AssertionError(
                    "Phase 5 sample feature timestamp predates exact source information"
                )
        membership_refs = [
            ref
            for ref in lineage["source_observation_refs"]
            if ref.get("capability") == "universe_membership"
        ]
        if (
            len(membership_refs) != 1
            or membership_refs[0] != expected_membership_ref
            or membership_event_utc > decision_time_utc
            or membership_available_utc > decision_time_utc
            or membership_valid_from_utc > decision_time_utc
            or decision_time_utc >= membership_valid_to_utc
        ):
            raise AssertionError(
                "Phase 5 sample membership identity or point-in-time interval is invalid"
            )
    trials = report.get("trials")
    if not isinstance(trials, list) or len(trials) != 6:
        raise AssertionError("Phase 5 report omitted raw trials")
    statuses = [item.get("status") for item in trials if isinstance(item, dict)]
    if statuses.count("failed") != 1 or statuses.count("abandoned") != 1:
        raise AssertionError("Phase 5 raw trial count omitted failed/abandoned variants")
    for trial in trials:
        if not isinstance(trial, dict):
            raise AssertionError("Phase 5 trial registry contains malformed evidence")
        returns = trial.get("net_returns")
        return_statuses = trial.get("return_statuses")
        timestamps = trial.get("return_timestamps_utc")
        if (
            not isinstance(returns, list)
            or not isinstance(return_statuses, list)
            or not isinstance(timestamps, list)
            or len(returns) != len(return_statuses)
            or len(returns) != len(timestamps)
        ):
            raise AssertionError("Phase 5 trial return values/statuses/calendar are not aligned")
        if any(
            value not in {"observed", "no_trade", "delisted", "missing"}
            for value in return_statuses
        ):
            raise AssertionError("Phase 5 trial registry contains an unknown return status")
    gates = report.get("gates")
    expected_gates = {
        "DATA_PIT",
        "CV_CHRONOLOGY",
        "PREPROCESSING",
        "TRIAL_REGISTRY",
        "DSR",
        "PBO",
        "COST_STRESS",
        "LEAKAGE",
        "SAMPLE_ADEQUACY",
        "REGIME",
        "RISK_LIMITS",
        "REPRODUCIBILITY",
    }
    if (
        not isinstance(gates, list)
        or {item.get("gate_code") for item in gates if isinstance(item, dict)} != expected_gates
    ):
        raise AssertionError("Phase 5 report omitted one or more mandatory gates")
    for gate in gates:
        if not isinstance(gate, dict) or not all(
            field in gate
            for field in ("inputs", "thresholds", "results", "warnings", "reason_codes")
        ):
            raise AssertionError("Phase 5 gate omitted numeric/audit evidence fields")
    for field in (
        "config_hash",
        "snapshot_bundle_sha256",
        "code_version_git_sha",
        "random_seed",
        "effective_trial_count",
        "created_at_utc",
        "decision_time_utc",
        "warnings",
        "reason_codes",
        "metrics",
        "folds",
        "preprocessing_fits",
        "source_observations",
        "sample_lineage_sha256",
        "sample_lineage",
        "oos_ledger",
        "cost_ledger",
    ):
        if field not in report:
            raise AssertionError(f"Phase 5 report omitted required audit artifact {field}")

    oos_ledger = report.get("oos_ledger")
    cost_ledger = report.get("cost_ledger")
    if not isinstance(oos_ledger, list) or len(oos_ledger) != 8:
        raise AssertionError("Phase 5 report omitted the deterministic OOS ledger")
    if not isinstance(cost_ledger, list) or len(cost_ledger) != len(oos_ledger) * 3:
        raise AssertionError("Phase 5 report omitted one or more required cost reruns")
    oos_status_by_sample: dict[str, str] = {}
    for entry in oos_ledger:
        if not isinstance(entry, dict) or not isinstance(entry.get("sample_id"), str):
            raise AssertionError("Phase 5 OOS ledger contains malformed evidence")
        sample_id = entry["sample_id"]
        lineage = lineage_by_sample.get(sample_id)
        if (
            lineage is None
            or entry.get("sample_sha256") != lineage.get("sample_sha256")
            or entry.get("source_observation_refs") != lineage.get("source_observation_refs")
            or entry.get("decision_time_utc") != lineage.get("decision_time_utc")
            or entry.get("return_status") not in {"observed", "no_trade", "delisted", "missing"}
        ):
            raise AssertionError("Phase 5 OOS row lost exact sample or return-status lineage")
        oos_status_by_sample[sample_id] = entry["return_status"]
    scenario_counts: dict[str, int] = {}
    for entry in cost_ledger:
        if not isinstance(entry, dict) or not isinstance(entry.get("sample_id"), str):
            raise AssertionError("Phase 5 cost ledger contains malformed evidence")
        sample_id = entry["sample_id"]
        if entry.get("return_status") != oos_status_by_sample.get(sample_id):
            raise AssertionError("Phase 5 cost row lost OOS return-status lineage")
        scenario_counts[sample_id] = scenario_counts.get(sample_id, 0) + 1
    if set(scenario_counts.values()) != {3}:
        raise AssertionError("Phase 5 cost scenarios do not preserve exact sample coverage")

    report_detail = request_json(f"{api_url}/v1/evaluation-reports/{artifact_id}")
    summaries = request_json(f"{api_url}/v1/evaluation-reports?limit=100")
    if (
        report_detail != report
        or not isinstance(summaries, list)
        or artifact_id
        not in {item.get("artifact_id") for item in summaries if isinstance(item, dict)}
    ):
        raise AssertionError("Phase 5 report create/read/list contract is incomplete")

    forbidden = dict(run_request)
    forbidden.update(
        {
            "metrics": {"sharpe": "99"},
            "artifact_sha256": "0" * 64,
            "thresholds": {"dsr": "0"},
            "promotion_state": "PASS_RESEARCH",
            "positions": [],
        }
    )
    validation = request_error_json(
        f"{api_url}/v1/evaluation-reports",
        expected_status=422,
        payload=forbidden,
    )
    if not isinstance(validation.get("detail"), list):
        raise AssertionError("Phase 5 rejected client authority without typed validation evidence")
    missing_policy = request_error_json(
        f"{api_url}/v1/evaluation-reports",
        expected_status=422,
        payload={**run_request, "policy_version": 999},
    )
    if (
        missing_policy.get("status") != "blocked"
        or missing_policy.get("promotion_state") != "BLOCKED_MISSING_POLICY"
        or missing_policy.get("artifact_type") != "blocked_synthetic_research_evaluation"
        or missing_policy.get("synthetic") is not True
        or missing_policy.get("no_real_performance_claimed") is not True
        or not isinstance(missing_policy.get("outcome_id"), str)
        or not isinstance(missing_policy.get("outcome_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", missing_policy["outcome_sha256"]) is None
        or "detail" in missing_policy
    ):
        raise AssertionError(
            "Phase 5 missing policy did not return a persisted sanitized blocked artifact"
        )
    outcome_id = missing_policy["outcome_id"]
    outcome_detail = request_json(f"{api_url}/v1/evaluation-outcomes/{outcome_id}")
    outcomes = request_json(f"{api_url}/v1/evaluation-outcomes?limit=100")
    if (
        outcome_detail != missing_policy
        or not isinstance(outcomes, list)
        or outcome_id not in {item.get("outcome_id") for item in outcomes if isinstance(item, dict)}
    ):
        raise AssertionError("Phase 5 blocked-outcome create/read/list contract is incomplete")

    print(
        "Phase 5 policy/report/blocked-outcome create-read-list, complete source lineage, "
        "return-status/cost evidence, deterministic retry, "
        "and server-authority proof passed "
        f"(report_id={artifact_id}, report_sha256={artifact_hash}, "
        f"policy_sha256={policy_hash}, config_hash={report['config_hash']}, "
        f"fixture_sha256={report['fixture_sha256']}, "
        f"snapshot_bundle_sha256={report['snapshot_bundle_sha256']}, "
        f"sample_lineage_sha256={sample_lineage_sha256})."
    )
    return artifact_id


def verify_phase6_api(api_url: str) -> dict[str, str]:
    gate_codes = [
        "DATA_PIT",
        "CV_CHRONOLOGY",
        "PREPROCESSING",
        "TRIAL_REGISTRY",
        "DSR",
        "PBO",
        "COST_STRESS",
        "LEAKAGE",
        "SAMPLE_ADEQUACY",
        "REGIME",
        "RISK_LIMITS",
        "REPRODUCIBILITY",
    ]
    family_capabilities = {
        "A_CROSS_SECTIONAL_EQUITY_RANKING": [
            "as_reported_fundamentals",
            "corporate_actions",
            "delistings",
            "macro_regime_inputs",
            "ohlcv",
            "security_master",
            "universe_membership",
        ],
        "B_TIME_SERIES_MOMENTUM_REGIME": [
            "corporate_actions",
            "delistings",
            "ohlcv",
            "security_master",
            "trading_calendar",
            "universe_membership",
            "volatility_return_inputs",
        ],
        "C_OFFICIAL_EVENT_TEXT_OVERLAY": [
            "official_document_event_metadata",
            "ohlcv",
            "security_master",
            "universe_membership",
        ],
    }
    one_source_constituent_counts = {
        "as_reported_fundamentals": 12,
        "corporate_actions": 1,
        "delistings": 1,
        "macro_regime_inputs": 3,
        "official_document_event_metadata": 5,
        "ohlcv": 852,
        "security_master": 11,
        "trading_calendar": 305,
        "universe_membership": 5,
        "volatility_return_inputs": 3,
    }
    if (
        sum(one_source_constituent_counts.values()) != 1198
        or one_source_constituent_counts["trading_calendar"] != 305
    ):
        raise AssertionError("Phase 6 one-source fixture accounting is internally inconsistent")
    configuration_families = {
        "phase6-a-pass-v2": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "phase6-a-fail-cost-v2": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "phase6-b-pass-v2": "B_TIME_SERIES_MOMENTUM_REGIME",
        "phase6-b-fail-crash-v2": "B_TIME_SERIES_MOMENTUM_REGIME",
        "phase6-c-pass-v2": "C_OFFICIAL_EVENT_TEXT_OVERLAY",
        "phase6-c-fail-corroboration-v2": "C_OFFICIAL_EVENT_TEXT_OVERLAY",
    }
    expected_states = {
        "phase6-a-pass-v2": "PASS_RESEARCH",
        "phase6-a-fail-cost-v2": "FAIL_REJECT",
        "phase6-b-pass-v2": "FAIL_REJECT",
        "phase6-b-fail-crash-v2": "FAIL_REJECT",
        "phase6-c-pass-v2": "FAIL_REJECT",
    }

    mapping_results = request_json(f"{api_url}/v1/mappings?limit=100")
    if not isinstance(mapping_results, list):
        raise AssertionError("Phase 6 could not list mapping authority")
    mappings: dict[str, dict[str, object]] = {}
    for item in mapping_results:
        if not isinstance(item, dict) or not isinstance(item.get("mapping"), dict):
            continue
        mapping = item["mapping"]
        family = mapping.get("canonical_family")
        if mapping.get("verdict") == "BUILD_RESEARCH" and isinstance(family, str):
            mappings[family] = mapping
    if set(family_capabilities) - set(mappings):
        raise AssertionError("Phase 6 could not resolve authorized BUILD_RESEARCH A/B/C mappings")

    snapshots_by_family: dict[str, list[str]] = {}
    snapshot_hashes: dict[str, str] = {}
    for family, capabilities in family_capabilities.items():
        snapshot_ids: list[str] = []
        for capability in capabilities:
            payload = {
                "mapping_id": mappings[family]["mapping_id"],
                "as_of_utc": "2024-01-03T00:00:00Z",
                "capability": capability,
                "mock_configuration_id": "phase6-synthetic-default-v2",
            }
            created = request_json(
                f"{api_url}/v1/data-snapshots",
                method="POST",
                payload=payload,
            )
            repeated = request_json(
                f"{api_url}/v1/data-snapshots",
                method="POST",
                payload=payload,
            )
            if not isinstance(created, dict) or created != repeated:
                raise AssertionError(f"Phase 6 {family}/{capability} snapshot was not idempotent")
            snapshot = created.get("snapshot")
            constituents = created.get("constituents")
            if (
                not isinstance(snapshot, dict)
                or not isinstance(constituents, list)
                or not constituents
            ):
                raise AssertionError(f"Phase 6 {capability} snapshot omitted immutable evidence")
            if len(constituents) != one_source_constituent_counts[capability]:
                raise AssertionError(
                    "Phase 6 one-source fixture count drifted for "
                    f"{capability}: {len(constituents)}"
                )
            snapshot_id = snapshot.get("snapshot_id")
            snapshot_sha256 = snapshot.get("snapshot_sha256")
            manifest = snapshot.get("manifest")
            manifest_payload = manifest.get("payload") if isinstance(manifest, dict) else None
            configuration = (
                manifest_payload.get("configuration")
                if isinstance(manifest_payload, dict)
                else None
            )
            adapter = (
                manifest_payload.get("adapter") if isinstance(manifest_payload, dict) else None
            )
            if (
                not isinstance(snapshot_id, str)
                or not isinstance(snapshot_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256) is None
                or any(item.get("snapshot_id") != snapshot_id for item in constituents)
                or not isinstance(configuration, dict)
                or configuration.get("configuration_id") != "phase6-synthetic-default-v2"
                or configuration.get("fixture_set_version") != PHASE_6_FIXTURE_SET_VERSION
                or not isinstance(adapter, dict)
                or adapter.get("adapter_version") != "phase6-synthetic-pit-adapter-v2"
            ):
                raise AssertionError(f"Phase 6 {capability} snapshot lineage is invalid")
            snapshot_ids.append(snapshot_id)
            snapshot_hashes[snapshot_id] = snapshot_sha256
        snapshots_by_family[family] = sorted(snapshot_ids)

    def payload_for(configuration_id: str) -> dict[str, object]:
        family = configuration_families[configuration_id]
        return {
            "mapping_id": mappings[family]["mapping_id"],
            "snapshot_ids": snapshots_by_family[family],
            "research_configuration_id": configuration_id,
        }

    barrier = Barrier(2)

    def create_a_pass() -> dict[str, object] | list[object]:
        barrier.wait()
        return request_json(
            f"{api_url}/v1/research-runs",
            method="POST",
            payload=payload_for("phase6-a-pass-v2"),
            timeout_seconds=PHASE_6_REQUEST_TIMEOUT_SECONDS,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent = tuple(executor.map(lambda _: create_a_pass(), range(2)))
    if not all(isinstance(item, dict) for item in concurrent) or concurrent[0] != concurrent[1]:
        raise AssertionError("Concurrent identical Phase 6 creation was not idempotent")

    artifacts: dict[str, dict[str, object]] = {"phase6-a-pass-v2": dict(concurrent[0])}
    for configuration_id in expected_states:
        if configuration_id == "phase6-a-pass-v2":
            continue
        created = request_json(
            f"{api_url}/v1/research-runs",
            method="POST",
            payload=payload_for(configuration_id),
            timeout_seconds=PHASE_6_REQUEST_TIMEOUT_SECONDS,
        )
        repeated = request_json(
            f"{api_url}/v1/research-runs",
            method="POST",
            payload=payload_for(configuration_id),
            timeout_seconds=PHASE_6_REQUEST_TIMEOUT_SECONDS,
        )
        if not isinstance(created, dict) or created != repeated:
            raise AssertionError(f"Phase 6 {configuration_id} run was not idempotent")
        artifacts[configuration_id] = created

    blocked = request_error_json(
        f"{api_url}/v1/research-runs",
        expected_status=422,
        payload=payload_for("phase6-c-fail-corroboration-v2"),
    )
    repeated_blocked = request_error_json(
        f"{api_url}/v1/research-runs",
        expected_status=422,
        payload=payload_for("phase6-c-fail-corroboration-v2"),
    )
    if (
        blocked != repeated_blocked
        or blocked.get("promotion_state") != "BLOCKED_MISSING_POLICY"
        or blocked.get("reason_codes") != ["official_corroboration_required"]
        or "detail" in blocked
    ):
        raise AssertionError("Phase 6 official-corroboration negative fixture did not fail closed")
    forbidden = {
        **payload_for("phase6-a-pass-v2"),
        "metrics": {},
        "artifact_sha256": "0" * 64,
        "thresholds": {},
        "created_at_utc": "2026-07-14T00:00:00Z",
        "trial_results": [],
        "promotion_state": "PASS_RESEARCH",
    }
    request_error_json(
        f"{api_url}/v1/research-runs",
        expected_status=422,
        payload=forbidden,
    )

    reports: dict[str, dict[str, object]] = {}
    run_ids: dict[str, str] = {}
    for configuration_id, artifact in artifacts.items():
        family = configuration_families[configuration_id]
        run_id = artifact.get("run_id")
        artifact_sha256 = artifact.get("artifact_sha256")
        if (
            not isinstance(run_id, str)
            or not isinstance(artifact_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is None
            or artifact.get("configuration_id") != configuration_id
            or artifact.get("artifact_schema_version") != "phase6-research-artifact-v2"
            or artifact.get("family") != family
            or artifact.get("status") != "completed"
            or artifact.get("synthetic") is not True
            or artifact.get("no_real_performance_claimed") is not True
            or artifact.get("pass_research_is_not_paper_approval") is not True
            or artifact.get("paper_approval_granted") is not False
            or artifact.get("disclaimer")
            != "Synthetic research only; no real performance or investment advice."
        ):
            raise AssertionError(f"Phase 6 {configuration_id} violated research-only boundaries")
        bindings = artifact.get("snapshot_bindings")
        rows = artifact.get("feature_rows")
        scores = artifact.get("scores")
        model_output_sets = artifact.get("model_output_sets")
        trial_economics = artifact.get("trial_economics")
        attempts = artifact.get("attempts")
        comparisons = artifact.get("baseline_comparisons")
        phase5_link = artifact.get("phase5_evaluation")
        specification = artifact.get("specification")
        if not all(
            isinstance(item, list)
            for item in (
                bindings,
                rows,
                scores,
                model_output_sets,
                trial_economics,
                attempts,
                comparisons,
            )
        ):
            raise AssertionError(f"Phase 6 {configuration_id} omitted explainable evidence")
        if not isinstance(phase5_link, dict):
            raise AssertionError(f"Phase 6 {configuration_id} omitted Phase 5 lineage")
        expected_cost_model_id = (
            PHASE_6_FAMILY_B_TRANSACTION_COST_MODEL_ID
            if family == "B_TIME_SERIES_MOMENTUM_REGIME"
            else "phase5-component-cost-model-v1"
        )
        if (
            not isinstance(specification, dict)
            or specification.get("transaction_cost_model_id") != expected_cost_model_id
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} omitted its versioned transaction-cost contract"
            )
        assert isinstance(bindings, list)
        assert isinstance(rows, list)
        assert isinstance(scores, list)
        assert isinstance(model_output_sets, list)
        assert isinstance(trial_economics, list)
        assert isinstance(attempts, list)
        assert isinstance(comparisons, list)
        if {item.get("snapshot_id") for item in bindings if isinstance(item, dict)} != set(
            snapshots_by_family[family]
        ) or any(
            snapshot_hashes.get(str(item.get("snapshot_id"))) != item.get("snapshot_sha256")
            for item in bindings
            if isinstance(item, dict)
        ):
            raise AssertionError(f"Phase 6 {configuration_id} lost snapshot lineage")
        row_ids = {item.get("row_id") for item in rows if isinstance(item, dict)}
        prepared_sample_ids = {item.get("sample_id") for item in rows if isinstance(item, dict)}
        if (
            not rows
            or len(prepared_sample_ids) != len(rows)
            or {item.get("feature_row_id") for item in scores if isinstance(item, dict)} != row_ids
            or len(model_output_sets) != 4
            or len(trial_economics) != 4
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} score/model-output evidence is incomplete"
            )
        reproduction = artifact.get("source_reproduction_audit")
        regime_evidence = artifact.get("regime_evidence")
        reproduction_bindings = (
            reproduction.get("snapshot_bindings") if isinstance(reproduction, dict) else None
        )
        canonical_artifact_bindings = tuple(
            sorted(
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in bindings
                if isinstance(item, dict)
            )
        )
        canonical_reproduction_bindings = (
            tuple(
                sorted(
                    json.dumps(item, sort_keys=True, separators=(",", ":"))
                    for item in reproduction_bindings
                    if isinstance(item, dict)
                )
            )
            if isinstance(reproduction_bindings, list)
            else None
        )
        if (
            not isinstance(reproduction, dict)
            or reproduction.get("schema_version") != "phase6-prepared-source-reproduction-audit-v1"
            or reproduction.get("exact_match") is not True
            or reproduction.get("configuration_id") != configuration_id
            or not isinstance(reproduction_bindings, list)
            or canonical_reproduction_bindings is None
            or len(canonical_reproduction_bindings) != len(reproduction_bindings)
            or len(set(canonical_reproduction_bindings)) != len(canonical_reproduction_bindings)
            or canonical_reproduction_bindings != canonical_artifact_bindings
            or len(canonical_artifact_bindings) != len(bindings)
            or len(set(canonical_artifact_bindings)) != len(canonical_artifact_bindings)
            or reproduction.get("supplied_pipeline_input_sha256")
            != artifact.get("pipeline_input_sha256")
            or reproduction.get("reproduced_pipeline_input_sha256")
            != artifact.get("pipeline_input_sha256")
            or reproduction.get("supplied_payload_sha256")
            != reproduction.get("reproduced_payload_sha256")
            or not isinstance(regime_evidence, dict)
            or regime_evidence.get("schema_version") != "phase6-prepared-regime-evidence-v2"
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} omitted deterministic reproduction/regime evidence"
            )
        expected_regime_state = (
            "available" if family == "A_CROSS_SECTIONAL_EQUITY_RANKING" else "unavailable"
        )
        if regime_evidence.get("evidence_state") != expected_regime_state:
            raise AssertionError(f"Phase 6 {configuration_id} claimed unsupported regime data")
        if expected_regime_state == "unavailable" and (
            regime_evidence.get("rate_observations") != []
            or regime_evidence.get("crisis_windows") != []
            or regime_evidence.get("unavailable_reason")
            != "required-regime-sources-not-authorized-for-family-v1"
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} did not explicitly fail closed on regime inputs"
            )
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("features"), list):
                raise AssertionError("Phase 6 feature row is malformed")
            decision = datetime.fromisoformat(str(row["decision_time_utc"]).replace("Z", "+00:00"))
            for feature in row["features"]:
                references = feature.get("source_references") if isinstance(feature, dict) else None
                if not isinstance(references, list) or not references:
                    raise AssertionError("Phase 6 feature omitted source lineage")
                for reference in references:
                    if (
                        not isinstance(reference, dict)
                        or reference.get("snapshot_id") not in snapshots_by_family[family]
                        or datetime.fromisoformat(
                            str(reference.get("available_at_utc")).replace("Z", "+00:00")
                        )
                        > decision
                    ):
                        raise AssertionError("Phase 6 feature used non-PIT source evidence")
        statuses = [item.get("status") for item in attempts if isinstance(item, dict)]
        if len(attempts) != 6 or statuses.count("failed") != 1 or statuses.count("abandoned") != 1:
            raise AssertionError(f"Phase 6 {configuration_id} attempt accounting is incomplete")
        if not comparisons:
            raise AssertionError(f"Phase 6 {configuration_id} omitted baseline comparisons")
        if (
            phase5_link.get("promotion_state") != expected_states[configuration_id]
            or phase5_link.get("gate_codes") != gate_codes
            or phase5_link.get("raw_trial_count") != 6
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(phase5_link.get("phase5_trial_set_sha256")),
            )
            is None
            or Decimal(str(phase5_link.get("effective_trial_count"))) <= 0
        ):
            raise AssertionError(f"Phase 6 {configuration_id} lost Phase 5 trial/gate lineage")
        report_id = phase5_link.get("evaluation_report_id")
        if not isinstance(report_id, str):
            raise AssertionError(f"Phase 6 {configuration_id} omitted its Phase 5 report")
        report = request_json(f"{api_url}/v1/evaluation-reports/{report_id}")
        if not isinstance(report, dict):
            raise AssertionError("Phase 6 linked Phase 5 report is unreadable")
        gates = report.get("gates")
        trials = report.get("trials")
        sample_lineage = report.get("sample_lineage")
        folds = report.get("folds")
        oos_ledger = report.get("oos_ledger")
        cost_ledger = report.get("cost_ledger")
        if (
            report.get("artifact_sha256") != phase5_link.get("evaluation_report_sha256")
            or report.get("promotion_state") != expected_states[configuration_id]
            or report.get("raw_trial_count") != 6
            or not isinstance(trials, list)
            or len(trials) != 6
            or not isinstance(gates, list)
            or [item.get("gate_code") for item in gates if isinstance(item, dict)] != gate_codes
            or not isinstance(sample_lineage, list)
            or not sample_lineage
            or not isinstance(folds, list)
            or not folds
            or not isinstance(oos_ledger, list)
            or not oos_ledger
            or not isinstance(cost_ledger, list)
            or not cost_ledger
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("feature_derivation"), dict)
                or item["feature_derivation"].get("schema_version")
                != "phase6-source-feature-derivation-v1"
                or item["feature_derivation"].get("formula_id")
                != "source-decimal-times-frozen-multiplier-quantized-1e-12-v1"
                for item in sample_lineage
            )
        ):
            raise AssertionError(f"Phase 6 {configuration_id} did not use Phase 5 unchanged")
        attempt_set = {
            (
                item.get("phase5_trial_id"),
                item.get("phase5_trial_key"),
                item.get("status"),
                item.get("configuration_sha256"),
            )
            for item in attempts
            if isinstance(item, dict)
        }
        trial_set = {
            (
                item.get("trial_id"),
                item.get("trial_key"),
                item.get("status"),
                item.get("config_sha256"),
            )
            for item in trials
            if isinstance(item, dict)
        }
        if len(attempt_set) != 6 or attempt_set != trial_set:
            raise AssertionError(
                f"Phase 6 {configuration_id} attempt set differs from Phase 5 trials"
            )

        completed_trials = {
            item.get("trial_key"): item
            for item in trials
            if isinstance(item, dict) and item.get("status") == "completed"
        }
        output_sets_by_key = {
            item.get("trial_key"): item for item in model_output_sets if isinstance(item, dict)
        }
        trial_economics_by_key = {
            item.get("trial_key"): item for item in trial_economics if isinstance(item, dict)
        }
        if (
            len(completed_trials) != 4
            or len(output_sets_by_key) != 4
            or len(trial_economics_by_key) != 4
            or set(completed_trials) != set(output_sets_by_key)
            or set(completed_trials) != set(trial_economics_by_key)
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} model-output registry differs from completed trials"
            )

        outer_sample_ids = [
            sample_id
            for fold in folds
            if isinstance(fold, dict) and fold.get("fold_kind") in {"outer", "cpcv"}
            for sample_id in fold.get("test_sample_ids", [])
        ]
        inner_sample_ids = list(
            dict.fromkeys(
                sample_id
                for fold in folds
                if isinstance(fold, dict) and fold.get("fold_kind") == "inner"
                for sample_id in fold.get("test_sample_ids", [])
            )
        )
        report_baseline_entries = {
            str(item.get("sample_id")): item
            for item in cost_ledger
            if isinstance(item, dict) and item.get("scenario") == "baseline"
        }
        report_baseline_costs = {
            sample_id: Decimal(str(item.get("total_cost")))
            for sample_id, item in report_baseline_entries.items()
        }
        if set(outer_sample_ids) != set(report_baseline_costs):
            raise AssertionError(
                f"Phase 6 {configuration_id} baseline costs do not cover exact OOS rows"
            )

        output_cells_by_trial: dict[str, dict[str, dict[str, object]]] = {}
        inner_net_by_trial: dict[str, dict[str, Decimal]] = {}
        baseline_entries_by_trial: dict[str, dict[str, dict[str, object]]] = {}
        for trial_key, output_set in output_sets_by_key.items():
            if not isinstance(trial_key, str):
                raise AssertionError("Phase 6 model-output registry has a malformed trial key")
            outputs = output_set.get("outputs")
            ledger_cells = output_set.get("ledger_cells")
            trial = completed_trials[trial_key]
            configuration = trial.get("configuration")
            required_configuration_keys = {
                "model",
                "variant",
                "phase6_pipeline_input_sha256",
                "phase6_model_output_sha256",
                "phase6_output_set_sha256",
                "phase6_label_sha256",
                "phase6_ledger_cell_set_sha256",
                "phase6_payoff_formula_id",
                "phase6_allocation_rules_json",
                "phase6_trial_weights_json",
                "phase6_trial_cost_ledger_json",
                "phase6_trial_cost_set_sha256",
                "inner_validation_gross_returns_json",
                "inner_validation_return_statuses_json",
                "outer_gross_returns_json",
            }
            if family == "B_TIME_SERIES_MOMENTUM_REGIME":
                required_configuration_keys.update(
                    {
                        "phase6_cost_volatility_projection_id",
                        "phase6_cost_volatility_quantum",
                    }
                )
            if (
                not isinstance(outputs, list)
                or not isinstance(ledger_cells, list)
                or output_set.get("schema_version") != "phase6-phase5-model-output-set-v2"
                or len(outputs) != len(rows)
                or len(ledger_cells) != len(rows)
                or not isinstance(configuration, dict)
                or set(configuration) != required_configuration_keys
                or configuration.get("model") != output_set.get("model_id")
                or configuration.get("phase6_pipeline_input_sha256")
                != artifact.get("pipeline_input_sha256")
                or configuration.get("phase6_model_output_sha256")
                != output_set.get("model_output_sha256")
                or configuration.get("phase6_output_set_sha256")
                != output_set.get("output_set_sha256")
                or configuration.get("phase6_payoff_formula_id")
                != "phase6-long-flat-weight-times-label-quantized-v1"
                or (
                    family == "B_TIME_SERIES_MOMENTUM_REGIME"
                    and (
                        configuration.get("phase6_cost_volatility_projection_id")
                        != PHASE_6_FAMILY_B_COST_VOLATILITY_PROJECTION_ID
                        or configuration.get("phase6_cost_volatility_quantum")
                        != PHASE_6_FAMILY_B_COST_VOLATILITY_QUANTUM
                    )
                )
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} lost model-output lineage"
                )
            outputs_by_sample = {
                item.get("sample_id"): Decimal(str(item.get("output_value")))
                for item in outputs
                if isinstance(item, dict)
            }
            cells_by_sample = {
                str(item.get("sample_id")): item for item in ledger_cells if isinstance(item, dict)
            }
            if (
                set(outputs_by_sample) != prepared_sample_ids
                or set(cells_by_sample) != prepared_sample_ids
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} ledger does not cover prepared rows"
                )
            weights = json.loads(str(configuration["phase6_trial_weights_json"]))
            allocation_rules = json.loads(str(configuration["phase6_allocation_rules_json"]))
            return_statuses = json.loads(
                str(configuration["inner_validation_return_statuses_json"])
            )
            trial_cost_entries = json.loads(str(configuration["phase6_trial_cost_ledger_json"]))
            if (
                not isinstance(weights, dict)
                or not isinstance(allocation_rules, dict)
                or not isinstance(return_statuses, dict)
                or not isinstance(trial_cost_entries, list)
                or set(weights) != prepared_sample_ids
                or set(allocation_rules) != prepared_sample_ids
                or len(trial_cost_entries) != len(rows) * 3
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} allocation/cost evidence is incomplete"
                )
            trial_costs_by_key = {
                (str(item.get("sample_id")), str(item.get("scenario"))): item
                for item in trial_cost_entries
                if isinstance(item, dict)
            }
            if len(trial_costs_by_key) != len(rows) * 3:
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} cost scenarios are not exact"
                )
            baseline_entries = {
                sample_id: trial_costs_by_key[(sample_id, "baseline")]
                for sample_id in prepared_sample_ids
            }
            baseline_entries_by_trial[trial_key] = baseline_entries
            economics = trial_economics_by_key[trial_key]
            sample_economics = economics.get("sample_economics")
            economics_by_sample = (
                {
                    str(item.get("sample_id")): item
                    for item in sample_economics
                    if isinstance(item, dict)
                }
                if isinstance(sample_economics, list)
                else {}
            )
            if (
                economics.get("model_id") != output_set.get("model_id")
                or economics.get("schema_version") != "phase6-trial-economics-v1"
                or economics.get("output_set_sha256") != output_set.get("output_set_sha256")
                or economics.get("cost_set_sha256")
                != configuration.get("phase6_trial_cost_set_sha256")
                or set(economics_by_sample) != prepared_sample_ids
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} artifact economics are incomplete"
                )
            for sample_id, cell in cells_by_sample.items():
                model_output = Decimal(str(cell.get("model_output")))
                label_value = Decimal(str(cell.get("label_value")))
                weight = Decimal(str(cell.get("synthetic_research_weight")))
                gross_return = Decimal(str(cell.get("synthetic_gross_return")))
                expected_gross_return = (weight * label_value).quantize(Decimal("0.000000000001"))
                expected_status = "observed" if weight == 1 else "no_trade"
                sample_costs = tuple(
                    trial_costs_by_key[(sample_id, scenario)]
                    for scenario in ("baseline", "all_cost_stress", "liquidity_stress")
                )
                persisted_economics = economics_by_sample[sample_id]
                persisted_cost_entries = persisted_economics.get("cost_entries")
                if (
                    model_output != outputs_by_sample[sample_id]
                    or weight not in {Decimal("0"), Decimal("1")}
                    or Decimal(str(weights[sample_id])) != weight
                    or allocation_rules[sample_id] != cell.get("allocation_rule_id")
                    or cell.get("return_status") != expected_status
                    or Decimal(str(persisted_economics.get("model_output"))) != model_output
                    or Decimal(str(persisted_economics.get("synthetic_research_weight"))) != weight
                    or persisted_economics.get("return_status") != expected_status
                    or persisted_economics.get("schema_version")
                    != "phase6-trial-sample-economics-v1"
                    or not isinstance(persisted_cost_entries, list)
                    or len(persisted_cost_entries) != len(sample_costs)
                    or any(
                        not phase6_cost_entries_match(
                            persisted_cost,
                            trial_cost,
                            require_identity=True,
                        )
                        for persisted_cost, trial_cost in zip(
                            persisted_cost_entries,
                            sample_costs,
                            strict=True,
                        )
                    )
                    or gross_return != expected_gross_return
                    or cell.get("trial_key") != trial_key
                    or cell.get("model_id") != output_set.get("model_id")
                    or cell.get("model_output_sha256") != output_set.get("model_output_sha256")
                    or cell.get("payoff_formula_id")
                    != "phase6-long-flat-weight-times-label-quantized-v1"
                    or not isinstance(cell.get("label_source_references"), list)
                    or not cell["label_source_references"]
                    or any(
                        item.get("return_status") != expected_status
                        or Decimal(str(item.get("gross_return"))) != gross_return
                        for item in sample_costs
                    )
                    or (
                        expected_status == "no_trade"
                        and any(
                            Decimal(str(item.get(field))) != 0
                            for item in sample_costs
                            for field in (
                                "requested_quantity",
                                "filled_quantity",
                                "rejected_quantity",
                                "unfilled_quantity",
                                "gross_return",
                                "fee_cost",
                                "spread_cost",
                                "impact_cost",
                                "latency_cost",
                                "borrow_cost",
                                "capacity_cost",
                                "total_cost",
                                "net_return",
                                "participation_rate",
                            )
                        )
                    )
                ):
                    raise AssertionError(
                        f"Phase 6 {configuration_id}/{trial_key}/{sample_id} ledger is not exact"
                    )

            inner_returns = json.loads(
                str(configuration.get("inner_validation_gross_returns_json"))
            )
            outer_returns = json.loads(str(configuration.get("outer_gross_returns_json")))
            if (
                not isinstance(inner_returns, dict)
                or not isinstance(outer_returns, dict)
                or set(inner_returns) != set(inner_sample_ids)
                or set(outer_returns) != set(outer_sample_ids)
                or any(
                    Decimal(str(value))
                    != Decimal(str(cells_by_sample[sample_id]["synthetic_gross_return"]))
                    for sample_id, value in inner_returns.items()
                )
                or any(
                    Decimal(str(value))
                    != Decimal(str(cells_by_sample[sample_id]["synthetic_gross_return"]))
                    for sample_id, value in outer_returns.items()
                )
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} trial maps do not match ledger cells"
                )
            if return_statuses != {
                sample_id: cells_by_sample[sample_id]["return_status"]
                for sample_id in inner_sample_ids
            }:
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} return statuses do not reconcile"
                )
            inner_net_by_trial[trial_key] = {
                str(sample_id): Decimal(str(baseline_entries[str(sample_id)]["net_return"]))
                for sample_id in inner_returns
            }
            expected_net_returns = [
                Decimal(str(baseline_entries[sample_id]["net_return"]))
                for sample_id in outer_sample_ids
            ]
            if [Decimal(str(item)) for item in trial.get("net_returns", [])] != (
                expected_net_returns
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{trial_key} net returns do not reconcile"
                )
            output_cells_by_trial[trial_key] = cells_by_sample

        trials_by_id = {
            str(item.get("trial_id")): item
            for item in completed_trials.values()
            if isinstance(item, dict)
        }
        expected_oos_pairs = {
            (str(fold.get("fold_id")), str(sample_id))
            for fold in folds
            if isinstance(fold, dict) and fold.get("fold_kind") in {"outer", "cpcv"}
            for sample_id in fold.get("test_sample_ids", [])
        }
        observed_oos_pairs = {
            (str(entry.get("fold_id")), str(entry.get("sample_id")))
            for entry in oos_ledger
            if isinstance(entry, dict)
        }
        if (
            len(outer_sample_ids) != len(set(outer_sample_ids))
            or len(oos_ledger) != len(expected_oos_pairs)
            or observed_oos_pairs != expected_oos_pairs
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} OOS ledger does not exactly cover outer folds"
            )
        selected_trial_id_by_fold: dict[str, str] = {}
        for outer_fold in (
            item
            for item in folds
            if isinstance(item, dict) and item.get("fold_kind") in {"outer", "cpcv"}
        ):
            outer_fold_id = str(outer_fold.get("fold_id"))
            validation_ids = [
                str(sample_id)
                for inner_fold in folds
                if isinstance(inner_fold, dict)
                and inner_fold.get("fold_kind") == "inner"
                and str(inner_fold.get("parent_fold_id")) == outer_fold_id
                for sample_id in inner_fold.get("test_sample_ids", [])
            ]
            if not validation_ids:
                raise AssertionError("Phase 6 outer fold has no inner validation evidence")
            selection_scores = {
                trial_key: sum(
                    (returns[sample_id] for sample_id in validation_ids),
                    Decimal("0"),
                )
                / Decimal(len(validation_ids))
                for trial_key, returns in inner_net_by_trial.items()
            }
            best_score = max(selection_scores.values())
            winners = [
                trial_key for trial_key, score in selection_scores.items() if score == best_score
            ]
            if len(winners) != 1:
                raise AssertionError("Phase 6 inner-fold model selection is not unique")
            selected_trial_id_by_fold[outer_fold_id] = str(
                completed_trials[winners[0]].get("trial_id")
            )

        decision_time_by_sample = {
            str(entry.get("sample_id")): str(entry.get("decision_time_utc"))
            for entry in oos_ledger
            if isinstance(entry, dict)
        }
        expected_trial_calendar = [decision_time_by_sample[str(item)] for item in outer_sample_ids]
        if any(
            [str(item) for item in trial.get("return_timestamps_utc", [])]
            != expected_trial_calendar
            for trial in completed_trials.values()
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} completed-trial calendars do not cover exact OOS rows"
            )
        for entry in oos_ledger:
            if not isinstance(entry, dict):
                raise AssertionError("Phase 6 OOS ledger contains malformed evidence")
            selected_trial_record = trials_by_id.get(str(entry.get("trial_id")))
            if selected_trial_record is None:
                raise AssertionError("Phase 6 OOS row does not identify a completed trial")
            if str(entry.get("trial_id")) != selected_trial_id_by_fold.get(
                str(entry.get("fold_id"))
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id} OOS row does not use its inner-fold winner"
                )
            trial_key = str(selected_trial_record.get("trial_key"))
            sample_id = str(entry.get("sample_id"))
            selected_cell = output_cells_by_trial[trial_key].get(sample_id)
            selected_baseline = baseline_entries_by_trial[trial_key].get(sample_id)
            if selected_cell is None or selected_baseline is None:
                raise AssertionError("Phase 6 OOS row has no selected model-output cell")
            gross_return = Decimal(str(selected_cell["synthetic_gross_return"]))
            report_selected_baseline = report_baseline_entries.get(sample_id)
            if (
                Decimal(str(entry.get("predicted_value")))
                != Decimal(str(selected_cell["model_output"]))
                or Decimal(str(entry.get("gross_return"))) != gross_return
                or Decimal(str(entry.get("baseline_net_return")))
                != Decimal(str(selected_baseline["net_return"]))
                or entry.get("return_status") != selected_cell.get("return_status")
                or report_selected_baseline is None
                or not phase6_cost_entries_match(
                    report_selected_baseline,
                    selected_baseline,
                    require_identity=False,
                )
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id}/{sample_id} selected OOS row does not reconcile"
                )

        policy = request_json(
            f"{api_url}/v1/evaluation-policies/{report['evaluation_policy_id']}"
            f"/versions/{report['evaluation_policy_version']}"
        )
        walk_forward = policy.get("walk_forward") if isinstance(policy, dict) else None
        if not isinstance(walk_forward, dict):
            raise AssertionError("Phase 6 linked policy omitted walk-forward geometry")
        confirmation_start = datetime.fromisoformat(
            str(walk_forward.get("final_confirmation_start_utc")).replace("Z", "+00:00")
        )
        confirmation_end = datetime.fromisoformat(
            str(walk_forward.get("final_confirmation_end_utc")).replace("Z", "+00:00")
        )
        confirmation = artifact.get("confirmation_interval")
        boundary_exclusions = artifact.get("boundary_exclusions")
        if not isinstance(confirmation, dict) or not isinstance(boundary_exclusions, list):
            raise AssertionError(f"Phase 6 {configuration_id} omitted confirmation evidence")
        confirmation_id = str(confirmation.get("sample_id"))
        boundary_ids = {
            str(item.get("sample_id")) for item in boundary_exclusions if isinstance(item, dict)
        }
        if (
            not boundary_ids
            or confirmation_id in prepared_sample_ids
            or boundary_ids & prepared_sample_ids
            or confirmation.get("schema_version") != "phase6-label-blind-confirmation-interval-v1"
            or not isinstance(confirmation.get("source_references"), list)
            or not confirmation["source_references"]
            or confirmation.get("label_value") is not None
            or confirmation.get("label_source_references") != []
            or confirmation.get("label_opened") is not False
            or datetime.fromisoformat(
                str(confirmation.get("interval_start_utc")).replace("Z", "+00:00")
            )
            != confirmation_start
            or datetime.fromisoformat(
                str(confirmation.get("interval_end_utc")).replace("Z", "+00:00")
            )
            != confirmation_end
            or any(
                not isinstance(item, dict)
                or item.get("schema_version") != "phase6-confirmation-boundary-exclusion-v1"
                or item.get("label_value") is not None
                or item.get("label_source_references") != []
                or item.get("label_opened") is not False
                for item in boundary_exclusions
            )
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} confirmation is not label-blind and predeclared"
            )
        forbidden_ids = {confirmation_id, *boundary_ids}
        report_sample_ids = {
            str(item.get("sample_id")) for item in sample_lineage if isinstance(item, dict)
        }
        if report_sample_ids != prepared_sample_ids | {confirmation_id}:
            raise AssertionError(
                f"Phase 6 {configuration_id} fixture does not exactly apply confirmation purge"
            )
        fold_sample_ids = {
            str(sample_id)
            for fold in folds
            if isinstance(fold, dict)
            for field in (
                "train_sample_ids",
                "purged_sample_ids",
                "test_sample_ids",
                "embargoed_sample_ids",
            )
            for sample_id in fold.get(field, [])
        }
        chronology_gate = next(
            (
                item
                for item in gates
                if isinstance(item, dict) and item.get("gate_code") == "CV_CHRONOLOGY"
            ),
            None,
        )
        chronology_inputs = (
            chronology_gate.get("inputs") if isinstance(chronology_gate, dict) else None
        )
        if (
            forbidden_ids & fold_sample_ids
            or not boundary_ids
            or not isinstance(chronology_inputs, dict)
            or chronology_inputs.get("confirmation_sample_count") != 1
            or chronology_inputs.get("post_confirmation_sample_count") != 0
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} confirmation/boundary evidence is incomplete"
            )
        reports[configuration_id] = report
        if request_json(f"{api_url}/v1/research-runs/{run_id}") != artifact:
            raise AssertionError(f"Phase 6 {configuration_id} detail is not byte-stable")
        run_ids[configuration_id] = run_id

    def gate(configuration_id: str, code: str) -> dict[str, object]:
        gates = reports[configuration_id].get("gates")
        assert isinstance(gates, list)
        matches = [
            item for item in gates if isinstance(item, dict) and item.get("gate_code") == code
        ]
        if len(matches) != 1:
            raise AssertionError(f"Phase 6 {configuration_id} has ambiguous {code} evidence")
        return matches[0]

    if any(gate("phase6-a-pass-v2", code).get("outcome") != "pass" for code in gate_codes):
        raise AssertionError("Phase 6 A positive fixture did not pass all 12 unchanged gates")
    a_fail_non_pass = {
        code: gate("phase6-a-fail-cost-v2", code)
        for code in gate_codes
        if gate("phase6-a-fail-cost-v2", code).get("outcome") != "pass"
    }
    if (
        set(a_fail_non_pass) != {"COST_STRESS"}
        or a_fail_non_pass["COST_STRESS"].get("outcome") != "fail"
        or a_fail_non_pass["COST_STRESS"].get("reason_codes")
        != ["stressed_edge_non_positive_or_policy_limit"]
    ):
        raise AssertionError("Phase 6 A cost-negative fixture did not reject only on cost")

    for configuration_id in ("phase6-b-pass-v2", "phase6-b-fail-crash-v2"):
        if (
            gate(configuration_id, "DSR").get("outcome") != "pass"
            or gate(configuration_id, "PBO").get("outcome") != "fail"
            or gate(configuration_id, "PBO").get("reason_codes") != ["pbo_above_frozen_threshold"]
            or gate(configuration_id, "REGIME").get("outcome") != "research_only"
            or set(gate(configuration_id, "REGIME").get("reason_codes", []))
            != {
                "volatility_regime_coverage_missing",
                "rate_regime_coverage_missing",
                "crisis_window_coverage_missing",
            }
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} did not truthfully reject on PBO/regime"
            )
    if (
        gate("phase6-c-pass-v2", "DSR").get("outcome") != "fail"
        or gate("phase6-c-pass-v2", "DSR").get("reason_codes") != ["dsr_below_frozen_threshold"]
        or gate("phase6-c-pass-v2", "PBO").get("outcome") != "fail"
        or gate("phase6-c-pass-v2", "PBO").get("reason_codes") != ["pbo_above_frozen_threshold"]
        or gate("phase6-c-pass-v2", "REGIME").get("outcome") != "research_only"
        or set(gate("phase6-c-pass-v2", "REGIME").get("reason_codes", []))
        != {"rate_regime_coverage_missing", "crisis_window_coverage_missing"}
    ):
        raise AssertionError("Phase 6 C did not truthfully reject on DSR/PBO/regime")

    for configuration_id in (
        "phase6-a-pass-v2",
        "phase6-b-pass-v2",
        "phase6-c-pass-v2",
    ):
        cost = gate(configuration_id, "COST_STRESS")
        results = cost.get("results")
        if (
            cost.get("outcome") != "pass"
            or not isinstance(results, dict)
            or Decimal(str(results.get("all_cost_net_return"))) <= 0
        ):
            raise AssertionError(f"Phase 6 {configuration_id} retained non-positive stressed edge")
    a_regime = artifacts["phase6-a-pass-v2"].get("regime_evidence")
    a_rate_observations = a_regime.get("rate_observations") if isinstance(a_regime, dict) else None
    a_crisis_windows = a_regime.get("crisis_windows") if isinstance(a_regime, dict) else None
    if (
        not isinstance(a_rate_observations, list)
        or len(a_rate_observations) != 2
        or {Decimal(str(item.get("rate_change"))) for item in a_rate_observations}
        != {Decimal("0.10"), Decimal("-0.20")}
        or any(
            not isinstance(item.get("source_reference"), dict)
            or item["source_reference"].get("capability") != "macro_regime_inputs"
            or item["source_reference"].get("record_type") != "macro_rate_observation"
            or item["source_reference"].get("available_at_utc") != item.get("released_at_utc")
            for item in a_rate_observations
        )
        or not isinstance(a_crisis_windows, list)
        or len(a_crisis_windows) != 1
        or a_crisis_windows[0].get("crisis_window_id") != "synthetic-predeclared-stress-2020-01"
        or not isinstance(a_crisis_windows[0].get("source_reference"), dict)
        or a_crisis_windows[0]["source_reference"].get("capability") != "macro_regime_inputs"
        or a_crisis_windows[0]["source_reference"].get("record_type") != "crisis_window_definition"
        or datetime.fromisoformat(
            str(a_crisis_windows[0].get("declared_at_utc")).replace("Z", "+00:00")
        )
        >= datetime.fromisoformat(
            str(a_crisis_windows[0].get("window_start_utc")).replace("Z", "+00:00")
        )
    ):
        raise AssertionError("Phase 6 A PIT macro-rate/crisis evidence is incomplete")

    a_evidence = artifacts["phase6-a-pass-v2"].get("family_evidence")
    if not isinstance(a_evidence, dict):
        raise AssertionError("Phase 6 A family evidence is missing")
    universe = a_evidence.get("universe")
    fits = a_evidence.get("train_only_sector_fits")
    capacity = a_evidence.get("capacity")
    if (
        a_evidence.get("frozen_feature_names")
        != ["liquidity", "momentum", "quality", "turnover", "value", "volatility"]
        or not isinstance(universe, list)
        or {item.get("listing_status") for item in universe if isinstance(item, dict)}
        < {"active", "delisted"}
        or not isinstance(fits, list)
        or len(fits) != 6
        or any(
            len(item.get("train_entity_ids", [])) < 2
            or len(item.get("train_entity_ids", [])) != len(set(item.get("train_entity_ids", [])))
            for item in fits
            if isinstance(item, dict)
        )
        or any(
            set(item.get("train_sample_ids", [])) & set(item.get("prohibited_sample_ids", []))
            for item in fits
            if isinstance(item, dict)
        )
        or not isinstance(capacity, dict)
        or capacity.get("capacity_limit_breached") is not False
    ):
        raise AssertionError("Phase 6 A universe, transform, or capacity evidence is incomplete")
    if not any(
        item.get("outcome") == "survives"
        for item in artifacts["phase6-a-pass-v2"]["baseline_comparisons"]
        if isinstance(item, dict)
    ):
        raise AssertionError("Phase 6 A did not survive a required baseline comparison")

    b_pass = artifacts["phase6-b-pass-v2"].get("family_evidence")
    b_fail = artifacts["phase6-b-fail-crash-v2"].get("family_evidence")
    if (
        not isinstance(b_pass, dict)
        or not isinstance(b_fail, dict)
        or b_pass.get("lag_windows") != [1, 5, 20, 63, 126, 252]
        or b_pass.get("nominal_feature_price_basis") != "raw_unadjusted"
        or b_pass.get("adjusted_return_formula_id") != "phase6-action-and-delisting-aware-return-v1"
        or b_pass.get("no_image_candlestick_or_named_pattern_classifier") is not True
        or b_pass.get("rate_evidence_available") is not False
        or b_pass.get("crisis_geometry_available") is not False
        or b_pass.get("crash_evidence_complete") is not False
        or b_pass.get("crash_concentration") is not None
        or b_fail.get("crash_evidence_complete") is not False
        or b_fail.get("crash_concentration") is not None
    ):
        raise AssertionError("Phase 6 B adjustment, lag, or crash evidence is incomplete")
    for evidence in (b_pass, b_fail):
        regimes = evidence.get("regime_results")
        if (
            not isinstance(regimes, list)
            or not regimes
            or any(
                not isinstance(item, dict)
                or not str(item.get("regime_id", "")).startswith("volatility:")
                or not isinstance(item.get("observation_count"), int)
                or item["observation_count"] <= 0
                or item.get("crash_window") is not False
                for item in regimes
            )
        ):
            raise AssertionError("Phase 6 B invented unavailable rate or crisis evidence")

    c_evidence = artifacts["phase6-c-pass-v2"].get("family_evidence")
    if not isinstance(c_evidence, dict):
        raise AssertionError("Phase 6 C family evidence is missing")
    extractions = c_evidence.get("extractions")
    corroborations = c_evidence.get("corroborations")
    if (
        not isinstance(extractions, list)
        or {item.get("correction_sequence") for item in extractions if isinstance(item, dict)}
        < {0, 1}
        or not isinstance(corroborations, list)
        or not corroborations
        or c_evidence.get("prompt_model_drift_visible") is not True
        or c_evidence.get("corrections_are_later_observations") is not True
        or c_evidence.get("llm_is_extraction_only") is not True
    ):
        raise AssertionError("Phase 6 C correction, drift, or extraction evidence is incomplete")
    official_ids = {
        item.get("official_source_version_id") for item in extractions if isinstance(item, dict)
    }
    official_document_hashes = {
        (item.get("official_source_version_id"), item.get("document_content_sha256"))
        for item in extractions
        if isinstance(item, dict)
    }
    if any(
        not isinstance(item, dict)
        or item.get("official_source_version_id") not in official_ids
        or (
            item.get("official_source_version_id"),
            item.get("official_document_sha256"),
        )
        not in official_document_hashes
        or item.get("exact_match") is not True
        or item.get("contributes_standalone") is not False
        for item in corroborations
    ):
        raise AssertionError("Phase 6 C social attention lacks exact official corroboration")
    for item in corroborations:
        assert isinstance(item, dict)
        social_reference = item.get("social_source_reference")
        official_reference = item.get("official_source_reference")
        if (
            not isinstance(social_reference, dict)
            or not isinstance(official_reference, dict)
            or social_reference.get("record_type") != "social_attention"
            or official_reference.get("record_type") != "official_document_content"
            or not isinstance(social_reference.get("source_record_id"), str)
            or not social_reference.get("source_record_id")
            or not isinstance(official_reference.get("source_record_id"), str)
            or not official_reference.get("source_record_id")
            or social_reference.get("source_record_id")
            == official_reference.get("source_record_id")
            or social_reference.get("raw_observation_id")
            == official_reference.get("raw_observation_id")
            or social_reference.get("normalized_observation_id")
            == official_reference.get("normalized_observation_id")
            or social_reference.get("snapshot_id")
            not in snapshots_by_family["C_OFFICIAL_EVENT_TEXT_OVERLAY"]
            or official_reference.get("snapshot_id")
            not in snapshots_by_family["C_OFFICIAL_EVENT_TEXT_OVERLAY"]
            or social_reference.get("instrument_id") != official_reference.get("instrument_id")
            or social_reference.get("listing_id") != official_reference.get("listing_id")
            or social_reference.get("normalized_content_sha256")
            == official_reference.get("normalized_content_sha256")
            or datetime.fromisoformat(
                str(official_reference.get("available_at_utc")).replace("Z", "+00:00")
            )
            > datetime.fromisoformat(
                str(social_reference.get("available_at_utc")).replace("Z", "+00:00")
            )
        ):
            raise AssertionError(
                "Phase 6 C social corroboration is not bound to separate immutable PIT records"
            )
    extraction_feature_names = {
        "novelty",
        "direction",
        "uncertainty",
        "risk_change",
        "event_tags",
    }
    if any(
        not isinstance(item.get("features"), dict)
        or set(item["features"]) != extraction_feature_names
        or item.get("output_boundary") != "structured_features_only"
        or item.get("extractor_kind") != "deterministic_mock"
        or not all(
            isinstance(item.get(field), str) and bool(item[field])
            for field in (
                "extractor_id",
                "extractor_version",
                "model_id",
                "prompt_version",
                "extraction_schema_version",
                "entity_id",
                "entity_resolution_method",
            )
        )
        or not isinstance(item.get("prompt_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", str(item.get("prompt_sha256"))) is None
        for item in extractions
        if isinstance(item, dict)
    ):
        raise AssertionError("Phase 6 C extraction exceeded its structured-feature boundary")
    expected_leakage_codes = {"L01", "L02", "L03", "L04", "L05", "L06"}
    expected_standard_schemas = {
        "L01": "phase5-leakage-l01-evidence-v1",
        "L05": "phase5-leakage-l05-evidence-v1",
    }
    for configuration_id in artifacts:
        leakage_gate = gate(configuration_id, "LEAKAGE")
        leakage_inputs = leakage_gate.get("inputs")
        if (
            leakage_gate.get("outcome") != "pass"
            or not isinstance(leakage_inputs, dict)
            or not isinstance(leakage_inputs.get("per_check_evidence_json"), str)
        ):
            raise AssertionError(
                f"Phase 6 {configuration_id} did not pass unchanged leakage checks"
            )
        leakage_evidence = json.loads(leakage_inputs["per_check_evidence_json"])
        findings = {item.get("code"): item for item in leakage_evidence if isinstance(item, dict)}
        if set(findings) != expected_leakage_codes:
            raise AssertionError(f"Phase 6 {configuration_id} did not run all six leakage blockers")
        for code, finding in findings.items():
            records = finding.get("evidence_records")
            if (
                not isinstance(records, list)
                or not records
                or any(
                    not isinstance(item, dict) or item.get("passed") is not True for item in records
                )
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id} has incomplete {code} leakage evidence"
                )
            expected_schema = expected_standard_schemas.get(str(code))
            if expected_schema is not None and any(
                item.get("schema_version") != expected_schema
                for item in records
                if isinstance(item, dict)
            ):
                raise AssertionError(
                    f"Phase 6 {configuration_id} special-cased unchanged {code} leakage logic"
                )

    listing = request_json(f"{api_url}/v1/research-runs?limit=100")
    if not isinstance(listing, list):
        raise AssertionError("Phase 6 research list is not an array")
    listed = {item.get("configuration_id"): item for item in listing if isinstance(item, dict)}
    if set(artifacts) - set(listed) or "phase6-c-fail-corroboration-v2" in listed:
        raise AssertionError("Phase 6 list omitted runs or persisted a blocked fixture")
    if any(
        item.get("synthetic") is not True
        or item.get("no_real_performance_claimed") is not True
        or item.get("pass_research_is_not_paper_approval") is not True
        for item in listed.values()
    ):
        raise AssertionError("Phase 6 list summary lost research-only flags")

    print(
        "Phase 6 v2 A PASS/A cost reject/B PBO-regime reject/C DSR-PBO-regime reject, "
        "exact PIT macro/source lineage, label-blind confirmation, trial economics, "
        "reproduction, unchanged Phase 5 gates, official corroboration, and concurrent "
        "idempotency passed."
    )
    return run_ids


def compose_exec(
    project: str,
    environment: dict[str, str],
    service: str,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "exec",
            "-T",
            service,
            *arguments,
        ],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        env=environment,
    )


def verify_phase3_changed_rule_version(
    project: str,
    environment: dict[str, str],
    card_id: str,
) -> None:
    script = f"""
import json
import os
from dataclasses import replace
from uuid import UUID

from fable5_mapping.repository import MappingRepository
from fable5_mapping.rules import CURRENT_RULE_SET

repository = MappingRepository(os.environ["FABLE5_DATABASE_URL"])
try:
    changed = replace(
        CURRENT_RULE_SET,
        version="phase3-canon-mapping-v2-verifier",
    )
    first = repository.create_mapping(UUID({card_id!r}), rule_set=changed)
    repeated = repository.create_mapping(UUID({card_id!r}), rule_set=changed)
    print(json.dumps({{
        "first_mapping_id": str(first.mapping.mapping_id),
        "repeated_mapping_id": str(repeated.mapping.mapping_id),
        "mapping_version": first.mapping.mapping_version,
        "rule_set_sha256": first.mapping.mapper_rule_set_sha256,
        "expected_rule_set_sha256": changed.sha256,
    }}))
finally:
    repository.dispose()
"""
    result = compose_exec(
        project,
        environment,
        "api",
        ["python", "-c", script],
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    if payload["first_mapping_id"] != payload["repeated_mapping_id"]:
        raise AssertionError("Changed Phase 3 rule set was not idempotent")
    if payload["mapping_version"] != 2:
        raise AssertionError(f"Changed Phase 3 rule set did not append version 2: {payload}")
    if (
        payload["rule_set_sha256"] != payload["expected_rule_set_sha256"]
        or payload["rule_set_sha256"] == PHASE_3_RULE_SET_SHA256
    ):
        raise AssertionError(f"Changed Phase 3 rule-set identity was not persisted: {payload}")

    version_query = (
        "SELECT string_agg(version_number::text, ',' ORDER BY version_number) "
        "FROM research_mapping_versions "
        f"WHERE card_id = '{card_id}'::uuid;"
    )
    versions = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", version_query],
    ).stdout.strip()
    if versions != "1,2":
        raise AssertionError(
            f"Changed Phase 3 rule set did not create gap-free versions: {versions}"
        )
    print("Phase 3 changed-rule-set append and retry idempotency proof passed.")


def verify_phase3_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_phase3_postgres.py", "-q"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=test_environment,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise AssertionError("Phase 3 isolated PostgreSQL acceptance tests failed")
    print("Phase 3 lineage, exact corroboration-set, and two-writer PostgreSQL tests passed.")


def verify_phase4_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_phase4_postgres.py", "-q"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=test_environment,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise AssertionError("Phase 4 isolated PostgreSQL acceptance tests failed")
    print(
        "Phase 4 lineage, as-of, exact corroboration, concurrent idempotency, rollback, and "
        "all-seven-table append-only PostgreSQL tests passed."
    )


def verify_phase5_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    test_environment["FABLE5_CODE_VERSION_GIT_SHA"] = environment["FABLE5_CODE_VERSION_GIT_SHA"]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_phase5_postgres.py", "-q"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=test_environment,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise AssertionError("Phase 5 isolated PostgreSQL acceptance tests failed")
    print(
        "Phase 5 concurrent idempotency, lineage, rollback, complete trial accounting, and "
        "append-only PostgreSQL tests passed."
    )


def verify_phase6_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    test_environment["FABLE5_CODE_VERSION_GIT_SHA"] = environment["FABLE5_CODE_VERSION_GIT_SHA"]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "services/research/tests/test_postgres.py",
            "-q",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=test_environment,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise AssertionError("Phase 6 isolated PostgreSQL acceptance tests failed")
    print(
        "Phase 6 concurrent idempotency, complete child lineage, payload consistency, and "
        "append-only PostgreSQL tests passed."
    )


def verify_phase2_queue_processing(
    project: str,
    environment: dict[str, str],
    queue_evidence: dict[str, str],
) -> None:
    request_id = queue_evidence["request_id"]
    event_query = (
        "SELECT string_agg(event_type, ',' ORDER BY event_sequence) "
        "FROM extraction_events "
        f"WHERE extraction_request_id = '{request_id}'::uuid;"
    )
    rendered_events = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", event_query],
    ).stdout.strip()
    events = rendered_events.split(",") if rendered_events else []
    if (
        len(events) != 4
        or set(events) != {"requested", "queued", "started", "succeeded"}
        or events[0] != "requested"
        or events[-1] != "succeeded"
        or events.index("started") > events.index("succeeded")
    ):
        raise AssertionError(
            f"Research queue event sequence was not complete and terminal: {rendered_events}"
        )

    job_id = queue_evidence["rq_job_id"]
    rq_check = (
        "from redis import Redis; "
        "from rq.job import Job; "
        "from fable5_jobs.config import WorkerSettings; "
        "connection=Redis.from_url(WorkerSettings().redis_url); "
        f"job=Job.fetch('{job_id}', connection=connection); "
        "print(job.get_status(refresh=True).value)"
    )
    rq_status = compose_exec(
        project,
        environment,
        "worker",
        ["python", "-c", rq_check],
    ).stdout.strip()
    if rq_status != "finished":
        raise AssertionError(f"RQ job did not finish on the research worker: {rq_status}")
    print(f"Phase 2 queue proof passed: terminal extraction events and finished RQ job {job_id}.")


def verify_phase2_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_2_TABLES
        for trigger_name in (
            f"{table}_immutable",
            f"{table}_no_truncate",
        )
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_2_TABLES
            for trigger in (
                f"{table}:{table}_immutable",
                f"{table}:{table}_no_truncate",
            )
        )
    )
    trigger_query = (
        "SELECT string_agg(c.relname || ':' || t.tgname, ',' "
        "ORDER BY c.relname, t.tgname) "
        "FROM pg_trigger AS t "
        "JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal "
        "AND t.tgenabled IN ('O','A') "
        "AND c.relname IN ("
        + ",".join(f"'{table}'" for table in PHASE_2_TABLES)
        + ") AND t.tgname IN ("
        + ",".join(f"'{trigger_name}'" for trigger_name in expected_trigger_names)
        + ");"
    )
    installed_triggers = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", trigger_query],
    ).stdout.strip()
    if installed_triggers != expected_triggers:
        raise AssertionError(
            f"Phase 2 append-only trigger catalog did not match the migration: {installed_triggers}"
        )

    update_columns = {
        "research_source_version_corroborations": "source_version_id",
        "card_official_corroborations": "card_id",
    }
    for table in PHASE_2_TABLES:
        column = update_columns.get(table, "id")
        statements = (
            f"UPDATE public.{table} SET {column} = {column};",
            f"DELETE FROM public.{table};",
            # CASCADE lets PostgreSQL reach the target's BEFORE TRUNCATE trigger instead of
            # rejecting parent tables at its foreign-key precheck.
            f"TRUNCATE public.{table} CASCADE;",
        )
        for statement in statements:
            result = compose_exec(
                project,
                environment,
                "postgres",
                ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", statement],
                check=False,
            )
            diagnostic = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0 or PHASE_2_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 2 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print(f"Phase 2 append-only trigger proof passed for {len(PHASE_2_TABLES)} tables.")


def verify_phase3_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_3_TABLES
        for trigger_name in (f"{table}_immutable", f"{table}_no_truncate")
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_3_TABLES
            for trigger in (f"{table}:{table}_immutable", f"{table}:{table}_no_truncate")
        )
    )
    trigger_query = (
        "SELECT string_agg(c.relname || ':' || t.tgname, ',' "
        "ORDER BY c.relname, t.tgname) "
        "FROM pg_trigger AS t "
        "JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal "
        "AND t.tgenabled IN ('O','A') "
        "AND c.relname IN ("
        + ",".join(f"'{table}'" for table in PHASE_3_TABLES)
        + ") AND t.tgname IN ("
        + ",".join(f"'{trigger_name}'" for trigger_name in expected_trigger_names)
        + ");"
    )
    installed_triggers = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", trigger_query],
    ).stdout.strip()
    if installed_triggers != expected_triggers:
        raise AssertionError(
            f"Phase 3 append-only trigger catalog did not match the migration: {installed_triggers}"
        )

    update_columns = {"mapping_official_corroborations": "mapping_id"}
    for table in PHASE_3_TABLES:
        row_count = compose_exec(
            project,
            environment,
            "postgres",
            [
                "psql",
                "-U",
                "fable5",
                "-d",
                "fable5",
                "-tAc",
                f"SELECT count(*) FROM public.{table};",
            ],
        ).stdout.strip()
        if not row_count.isdigit() or int(row_count) < 1:
            raise AssertionError(f"Phase 3 append-only proof has no persisted row in {table}")

        column = update_columns.get(table, "id")
        statements = (
            f"UPDATE public.{table} SET {column} = {column};",
            f"DELETE FROM public.{table};",
            f"TRUNCATE public.{table} CASCADE;",
        )
        for statement in statements:
            result = compose_exec(
                project,
                environment,
                "postgres",
                ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", statement],
                check=False,
            )
            diagnostic = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0 or PHASE_3_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 3 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print(f"Phase 3 append-only trigger proof passed for {len(PHASE_3_TABLES)} tables.")


def verify_phase5_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_5_TABLES
        for trigger_name in (f"{table}_immutable", f"{table}_no_truncate")
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_5_TABLES
            for trigger in (f"{table}:{table}_immutable", f"{table}:{table}_no_truncate")
        )
    )
    trigger_query = (
        "SELECT string_agg(c.relname || ':' || t.tgname, ',' "
        "ORDER BY c.relname, t.tgname) "
        "FROM pg_trigger AS t "
        "JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal "
        "AND t.tgenabled IN ('O','A') "
        "AND c.relname IN ("
        + ",".join(f"'{table}'" for table in PHASE_5_TABLES)
        + ") AND t.tgname IN ("
        + ",".join(f"'{trigger_name}'" for trigger_name in expected_trigger_names)
        + ");"
    )
    installed_triggers = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", trigger_query],
    ).stdout.strip()
    if installed_triggers != expected_triggers:
        raise AssertionError(
            f"Phase 5 append-only trigger catalog did not match the migration: {installed_triggers}"
        )

    for table in PHASE_5_TABLES:
        row_count = compose_exec(
            project,
            environment,
            "postgres",
            [
                "psql",
                "-U",
                "fable5",
                "-d",
                "fable5",
                "-tAc",
                f"SELECT count(*) FROM public.{table};",
            ],
        ).stdout.strip()
        if not row_count.isdigit() or int(row_count) < 1:
            raise AssertionError(f"Phase 5 append-only proof has no persisted row in {table}")
        column = compose_exec(
            project,
            environment,
            "postgres",
            [
                "psql",
                "-U",
                "fable5",
                "-d",
                "fable5",
                "-tAc",
                "SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema = 'public' AND table_name = '{table}' "
                "ORDER BY ordinal_position LIMIT 1;",
            ],
        ).stdout.strip()
        if not column:
            raise AssertionError(f"Phase 5 append-only proof found no column in {table}")
        statements = (
            f'UPDATE public.{table} SET "{column}" = "{column}";',
            f"DELETE FROM public.{table};",
            f"TRUNCATE public.{table} CASCADE;",
        )
        for statement in statements:
            result = compose_exec(
                project,
                environment,
                "postgres",
                ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", statement],
                check=False,
            )
            diagnostic = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0 or PHASE_5_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 5 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print(f"Phase 5 append-only trigger proof passed for {len(PHASE_5_TABLES)} tables.")


def verify_phase6_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_6_TABLES
        for trigger_name in (f"{table}_immutable", f"{table}_no_truncate")
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_6_TABLES
            for trigger in (f"{table}:{table}_immutable", f"{table}:{table}_no_truncate")
        )
    )
    trigger_query = (
        "SELECT string_agg(c.relname || ':' || t.tgname, ',' "
        "ORDER BY c.relname, t.tgname) "
        "FROM pg_trigger AS t "
        "JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal "
        "AND t.tgenabled IN ('O','A') "
        "AND c.relname IN ("
        + ",".join(f"'{table}'" for table in PHASE_6_TABLES)
        + ") AND t.tgname IN ("
        + ",".join(f"'{trigger_name}'" for trigger_name in expected_trigger_names)
        + ");"
    )
    installed_triggers = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", trigger_query],
    ).stdout.strip()
    if installed_triggers != expected_triggers:
        raise AssertionError(
            f"Phase 6 append-only trigger catalog did not match the migration: {installed_triggers}"
        )

    for table in PHASE_6_TABLES:
        row_count = compose_exec(
            project,
            environment,
            "postgres",
            [
                "psql",
                "-U",
                "fable5",
                "-d",
                "fable5",
                "-tAc",
                f"SELECT count(*) FROM public.{table};",
            ],
        ).stdout.strip()
        if not row_count.isdigit() or int(row_count) < 1:
            raise AssertionError(f"Phase 6 append-only proof has no persisted row in {table}")
        column = compose_exec(
            project,
            environment,
            "postgres",
            [
                "psql",
                "-U",
                "fable5",
                "-d",
                "fable5",
                "-tAc",
                "SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema = 'public' AND table_name = '{table}' "
                "ORDER BY ordinal_position LIMIT 1;",
            ],
        ).stdout.strip()
        if not column:
            raise AssertionError(f"Phase 6 append-only proof found no column in {table}")
        statements = (
            f'UPDATE public.{table} SET "{column}" = "{column}";',
            f"DELETE FROM public.{table};",
            f"TRUNCATE public.{table} CASCADE;",
        )
        for statement in statements:
            result = compose_exec(
                project,
                environment,
                "postgres",
                ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", statement],
                check=False,
            )
            diagnostic = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0 or PHASE_6_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 6 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print(f"Phase 6 append-only trigger proof passed for {len(PHASE_6_TABLES)} tables.")


def snapshot_tables(
    project: str, environment: dict[str, str], tables: tuple[str, ...]
) -> dict[str, tuple[int, str]]:
    snapshots: dict[str, tuple[int, str]] = {}
    for table in tables:
        query = (
            "SELECT COALESCE(jsonb_agg(to_jsonb(snapshot_row) "
            "ORDER BY to_jsonb(snapshot_row)::text), '[]'::jsonb)::text "
            f"FROM public.{table} AS snapshot_row;"
        )
        rendered = compose_exec(
            project,
            environment,
            "postgres",
            ["psql", "-U", "fable5", "-d", "fable5", "-tAc", query],
        ).stdout.strip()
        rows = json.loads(rendered or "[]")
        if not isinstance(rows, list):
            raise AssertionError(f"Stable snapshot query for {table} did not return a JSON array")
        canonical = json.dumps(
            rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        snapshots[table] = (len(rows), hashlib.sha256(canonical).hexdigest())
    return snapshots


def assert_snapshots_equal(
    expected: dict[str, tuple[int, str]], actual: dict[str, tuple[int, str]], stage: str
) -> None:
    if actual != expected:
        differences = {
            table: {"expected": expected.get(table), "actual": actual.get(table)}
            for table in sorted(set(expected) | set(actual))
            if expected.get(table) != actual.get(table)
        }
        raise AssertionError(f"Earlier-phase rows changed {stage}: {differences}")


def verify_phase2_migration_cycle(project: str, environment: dict[str, str]) -> None:
    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0001_phase1",
        ],
        project=project,
        env=environment,
    )
    query = (
        "SELECT to_regclass('public.research_audit_events') IS NOT NULL, "
        "to_regclass('public.trading_idea_cards') IS NULL;"
    )
    result = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", query],
    ).stdout.strip()
    if result != "t|t":
        raise AssertionError(f"Phase 2 downgrade did not preserve only the Phase 1 spine: {result}")
    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0002_phase2",
        ],
        project=project,
        env=environment,
    )
    restored_query = (
        "SELECT version_num, "
        "to_regclass('public.research_audit_events') IS NOT NULL, "
        "to_regclass('public.research_source_versions') IS NOT NULL, "
        "to_regclass('public.extraction_events') IS NOT NULL, "
        "to_regclass('public.trading_idea_cards') IS NOT NULL, "
        "to_regclass('public.research_memos') IS NOT NULL "
        "FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_query],
    ).stdout.strip()
    if restored != "0002_phase2|t|t|t|t|t":
        raise AssertionError(f"Phase 2 re-upgrade did not restore its exact schema: {restored}")
    print("Phase 2 migration downgrade/re-upgrade proof passed at revision 0002_phase2.")


def verify_phase3_migration_cycle(project: str, environment: dict[str, str]) -> None:
    earlier_tables = ("research_audit_events", *PHASE_2_TABLES)
    before = snapshot_tables(project, environment, earlier_tables)
    print(
        "Phase 3 earlier-table snapshots: "
        + json.dumps(
            {
                table: {"row_count": count, "sha256": digest}
                for table, (count, digest) in before.items()
            },
            sort_keys=True,
        )
    )

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0002_phase2",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_3_TABLES)
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    if downgraded != "0002_phase2|t|t|t":
        raise AssertionError(f"Phase 3 downgrade did not remove only Phase 3 tables: {downgraded}")
    after_downgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_downgrade, "during downgrade to 0002_phase2")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0003_phase3",
        ],
        project=project,
        env=environment,
    )
    restored_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_3_TABLES)
        + " FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_query],
    ).stdout.strip()
    if restored != "0003_phase3|t|t|t":
        raise AssertionError(f"Phase 3 re-upgrade did not restore revision 0003: {restored}")
    after_reupgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_reupgrade, "during re-upgrade to 0003_phase3")
    print(
        "Phase 3 downgrade/re-upgrade preserved research_audit_events and all eight Phase 2 tables."
    )


def verify_phase4_migration_cycle(project: str, environment: dict[str, str]) -> None:
    earlier_tables = ("research_audit_events", *PHASE_2_TABLES, *PHASE_3_TABLES)
    audit_fixture_id = "00000000-0000-5000-8000-000000000004"
    audit_insert = (
        "INSERT INTO research_audit_events "
        "(id,event_type,config_hash,data_snapshot_id,git_sha,random_seed,trial_count,payload) "
        f"VALUES ('{audit_fixture_id}'::uuid,'phase4_migration_preservation_fixture',"
        f"'{'4' * 64}','phase4-synthetic-preservation',"
        "'24e243e373ec6c6aacad22cf47505c50cc7bbcaa',4,1,"
        '\'{"fixture":"phase4_migration_preservation","synthetic":true}\'::jsonb) '
        "ON CONFLICT (id) DO NOTHING;"
    )
    compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", audit_insert],
    )
    before = snapshot_tables(project, environment, earlier_tables)
    if len(before) != 12:
        raise AssertionError("Phase 4 migration proof did not cover all 12 Phase 1-3 tables")
    empty_earlier_tables = sorted(table for table, (count, _) in before.items() if count < 1)
    if empty_earlier_tables:
        raise AssertionError(
            "Phase 4 migration proof requires preserved evidence in every earlier table: "
            + ", ".join(empty_earlier_tables)
        )
    print(
        "Phase 4 earlier-table snapshots: "
        + json.dumps(
            {
                table: {"row_count": count, "sha256": digest}
                for table, (count, digest) in before.items()
            },
            sort_keys=True,
        )
    )

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0003_phase3",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_4_TABLES)
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    expected_downgraded = "0003_phase3|" + "|".join("t" for _ in PHASE_4_TABLES)
    if downgraded != expected_downgraded:
        raise AssertionError(f"Phase 4 downgrade did not remove only Phase 4 tables: {downgraded}")
    after_downgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_downgrade, "during downgrade to 0003_phase3")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0004_phase4",
        ],
        project=project,
        env=environment,
    )
    restored_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_4_TABLES)
        + " FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_query],
    ).stdout.strip()
    expected_restored = "0004_phase4|" + "|".join("t" for _ in PHASE_4_TABLES)
    if restored != expected_restored:
        raise AssertionError(f"Phase 4 re-upgrade did not restore revision 0004: {restored}")
    after_reupgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_reupgrade, "during re-upgrade to 0004_phase4")
    print(
        "Phase 4 0004->0003->0004 migration cycle preserved all 12 Phase 1-3 tables "
        "byte-identically."
    )


def verify_phase5_migration_cycle(project: str, environment: dict[str, str]) -> None:
    earlier_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
    )
    git_sha = environment.get("FABLE5_CODE_VERSION_GIT_SHA")
    if git_sha is None or re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise AssertionError("Phase 5 migration proof requires the validated host git SHA")
    audit_fixture_id = "00000000-0000-5000-8000-000000000005"
    audit_insert = (
        "INSERT INTO research_audit_events "
        "(id,event_type,config_hash,data_snapshot_id,git_sha,random_seed,trial_count,payload) "
        f"VALUES ('{audit_fixture_id}'::uuid,'phase5_migration_preservation_fixture',"
        f"'{'5' * 64}','phase5-synthetic-preservation','{git_sha}',5,1,"
        '\'{"fixture":"phase5_migration_preservation","synthetic":true}\'::jsonb) '
        "ON CONFLICT (id) DO NOTHING;"
    )
    compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", audit_insert],
    )
    before = snapshot_tables(project, environment, earlier_tables)
    if len(before) != 19:
        raise AssertionError("Phase 5 migration proof did not cover all 19 Phase 1-4 tables")
    empty_earlier_tables = sorted(table for table, (count, _) in before.items() if count < 1)
    if empty_earlier_tables:
        raise AssertionError(
            "Phase 5 migration proof requires preserved evidence in every earlier table: "
            + ", ".join(empty_earlier_tables)
        )
    print(
        "Phase 5 earlier-table snapshots: "
        + json.dumps(
            {
                table: {"row_count": count, "sha256": digest}
                for table, (count, digest) in before.items()
            },
            sort_keys=True,
        )
    )

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0004_phase4",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_5_TABLES)
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    expected_downgraded = "0004_phase4|" + "|".join("t" for _ in PHASE_5_TABLES)
    if downgraded != expected_downgraded:
        raise AssertionError(f"Phase 5 downgrade did not remove only Phase 5 tables: {downgraded}")
    after_downgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_downgrade, "during downgrade to 0004_phase4")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0005_phase5",
        ],
        project=project,
        env=environment,
    )
    restored_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_5_TABLES)
        + " FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_query],
    ).stdout.strip()
    expected_restored = "0005_phase5|" + "|".join("t" for _ in PHASE_5_TABLES)
    if restored != expected_restored:
        raise AssertionError(f"Phase 5 re-upgrade did not restore revision 0005: {restored}")
    after_reupgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_reupgrade, "during re-upgrade to 0005_phase5")
    print(
        "Phase 5 0005->0004->0005 migration cycle preserved all 19 Phase 1-4 tables "
        "byte-identically."
    )


def verify_phase6_migration_cycle(project: str, environment: dict[str, str]) -> None:
    earlier_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
        *PHASE_5_TABLES,
    )
    git_sha = environment.get("FABLE5_CODE_VERSION_GIT_SHA")
    if git_sha is None or re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise AssertionError("Phase 6 migration proof requires the validated host git SHA")
    audit_fixture_id = "00000000-0000-5000-8000-000000000006"
    audit_insert = (
        "INSERT INTO research_audit_events "
        "(id,event_type,config_hash,data_snapshot_id,git_sha,random_seed,trial_count,payload) "
        f"VALUES ('{audit_fixture_id}'::uuid,'phase6_migration_preservation_fixture',"
        f"'{'6' * 64}','phase6-synthetic-preservation','{git_sha}',6,1,"
        '\'{"fixture":"phase6_migration_preservation","synthetic":true}\'::jsonb) '
        "ON CONFLICT (id) DO NOTHING;"
    )
    compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", audit_insert],
    )
    before = snapshot_tables(project, environment, earlier_tables)
    if len(before) != 31:
        raise AssertionError("Phase 6 migration proof did not cover all 31 Phase 1-5 tables")
    empty_earlier_tables = sorted(table for table, (count, _) in before.items() if count < 1)
    if empty_earlier_tables:
        raise AssertionError(
            "Phase 6 migration proof requires preserved evidence in every earlier table: "
            + ", ".join(empty_earlier_tables)
        )
    print(
        "Phase 6 earlier-table snapshots: "
        + json.dumps(
            {
                table: {"row_count": count, "sha256": digest}
                for table, (count, digest) in before.items()
            },
            sort_keys=True,
        )
    )

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0005_phase5",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_6_TABLES)
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    expected_downgraded = "0005_phase5|" + "|".join("t" for _ in PHASE_6_TABLES)
    if downgraded != expected_downgraded:
        raise AssertionError(f"Phase 6 downgrade did not remove only Phase 6 tables: {downgraded}")

    restored_base_query = (
        "SELECT "
        "to_regprocedure('validate_phase5_report_source_lineage(uuid)') IS NOT NULL, "
        "to_regprocedure('validate_phase5_report_source_lineage_phase5_base(uuid)') IS NULL, "
        "position('sector_classification' in pg_get_functiondef("
        "'phase4_record_type_matches_capability(text,text)'::regprocedure)) = 0, "
        "position('official_document_content' in pg_get_functiondef("
        "'phase4_record_type_matches_capability(text,text)'::regprocedure)) = 0, "
        "position('social_attention' in pg_get_functiondef("
        "'phase4_record_type_matches_capability(text,text)'::regprocedure)) = 0, "
        "position('macro_regime_inputs' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_snapshot_capability')) = 0, "
        "position('macro_rate_observation' in pg_get_functiondef("
        "'validate_phase4_normalized_observation()'::regprocedure)) = 0, "
        "position('phase6-synthetic-pit-fixtures-v1' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_snapshot_frozen_versions')) = 0, "
        "position('phase6-data-contract-quality-v1' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_quality_finding_identities')) = 0, "
        "position('official_corroboration_mismatch' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_quality_finding_code')) = 0, "
        "position('B_TIME_SERIES_MOMENTUM_REGIME' in pg_get_functiondef("
        "'validate_phase4_snapshot_request()'::regprocedure)) > 0, "
        "encode(sha256(convert_to((SELECT prosrc FROM pg_proc WHERE oid = "
        "'phase4_record_type_matches_capability(text,text)'::regprocedure), "
        "'UTF8')), 'hex') = '"
        + PHASE_4_BASE_FUNCTION_PROSRC_SHA256["phase4_record_type_matches_capability(text,text)"]
        + "', encode(sha256(convert_to((SELECT prosrc FROM pg_proc WHERE oid = "
        "'validate_phase4_snapshot_request()'::regprocedure), 'UTF8')), 'hex') = '"
        + PHASE_4_BASE_FUNCTION_PROSRC_SHA256["validate_phase4_snapshot_request()"]
        + "', encode(sha256(convert_to((SELECT prosrc FROM pg_proc WHERE oid = "
        "'validate_phase4_normalized_observation()'::regprocedure), 'UTF8')), 'hex') = '"
        + PHASE_4_BASE_FUNCTION_PROSRC_SHA256["validate_phase4_normalized_observation()"]
        + "';"
    )
    restored_base = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_base_query],
    ).stdout.strip()
    if restored_base != "t|t|t|t|t|t|t|t|t|t|t|t|t|t":
        raise AssertionError(
            "Phase 6 downgrade did not restore the exact Phase 4/5 function authority: "
            f"{restored_base}"
        )
    after_downgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_downgrade, "during downgrade to 0005_phase5")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0006_phase6",
        ],
        project=project,
        env=environment,
    )
    restored_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_6_TABLES)
        + ", to_regprocedure('validate_phase5_report_source_lineage(uuid)') IS NOT NULL"
        + ", to_regprocedure("
        "'validate_phase5_report_source_lineage_phase5_base(uuid)') IS NOT NULL"
        + ", position('social_attention' in pg_get_functiondef("
        "'phase4_record_type_matches_capability(text,text)'::regprocedure)) > 0"
        + ", position('macro_regime_inputs' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_snapshot_capability')) > 0"
        + ", position('macro_rate_observation' in pg_get_functiondef("
        "'validate_phase4_normalized_observation()'::regprocedure)) > 0"
        + ", position('phase6-synthetic-pit-fixtures-v1' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_snapshot_frozen_versions')) > 0"
        + ", position('phase6-data-contract-quality-v1' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_quality_finding_identities')) > 0"
        + ", position('official_corroboration_mismatch' in ("
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_data_quality_finding_code')) > 0" + " FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", restored_query],
    ).stdout.strip()
    expected_restored = "0006_phase6|" + "|".join("t" for _ in range(len(PHASE_6_TABLES) + 8))
    if restored != expected_restored:
        raise AssertionError(f"Phase 6 re-upgrade did not restore revision 0006: {restored}")
    after_reupgrade = snapshot_tables(project, environment, earlier_tables)
    assert_snapshots_equal(before, after_reupgrade, "during re-upgrade to 0006_phase6")
    print(
        "Phase 6 0006->0005->0006 migration cycle preserved all 31 Phase 1-5 tables "
        "byte-identically and restored the exact Phase 4/5 function boundaries."
    )


def wait_for_frontend(url: str, timeout: int = 60) -> str:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - integration-only polling
            last_error = exc
        time.sleep(2)
    raise AssertionError(f"Frontend did not become ready: {last_error}")


def verify_compose(phase: int = 1) -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required for full verification; use --static-only otherwise.")

    project = f"fable5_acceptance_{uuid.uuid4().hex[:8]}"
    environment, api_url, frontend_url = acceptance_environment(phase)
    try:
        run(["config", "--quiet"], project=project, env=environment)
        run(
            ["up", "--detach", "--build", "--wait", "--wait-timeout", "240"],
            project=project,
            env=environment,
        )

        health = fetch_json(f"{api_url}/health")
        expected_health = {
            "status": "ok",
            "service": "api",
            "mode": "research-paper-only",
        }
        if health != expected_health:
            raise AssertionError(f"Unexpected health response: {health}")

        ready = fetch_json(f"{api_url}/ready")
        if ready.get("status") != "ready":
            raise AssertionError(f"Unexpected readiness response: {ready}")

        html = wait_for_frontend(frontend_url)
        for label in ("Idea Intake", "Research Lab", "Paper Trading", "Risk / Compliance"):
            if label not in html:
                raise AssertionError(f"Frontend HTML is missing navigation label: {label}")

        pong = subprocess.run(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "exec",
                "-T",
                "redis",
                "redis-cli",
                "ping",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
        if pong != "PONG":
            raise AssertionError(f"Redis health check returned {pong!r}")

        if phase >= 2:
            queue_evidence = verify_phase2_api(api_url)
            verify_phase2_queue_processing(project, environment, queue_evidence)
            verify_phase2_append_only(project, environment)
            if phase == 2:
                verify_phase2_migration_cycle(project, environment)
                print("Full Compose Phase 2 verification passed.")
            else:
                phase3_card_id = verify_phase3_api(api_url)
                verify_phase3_changed_rule_version(project, environment, phase3_card_id)
                verify_phase3_postgres_acceptance(environment)
                verify_phase3_append_only(project, environment)
                if phase == 3:
                    verify_phase3_migration_cycle(project, environment)
                    print("Full Compose Phase 3 verification passed.")
                else:
                    phase4_snapshot_id = verify_phase4_api(api_url)
                    verify_phase4_postgres_acceptance(environment)
                    if phase == 4:
                        verify_phase4_migration_cycle(project, environment)
                        print("Full Compose Phase 4 verification passed.")
                    else:
                        verify_phase5_api(api_url, phase4_snapshot_id)
                        verify_phase5_postgres_acceptance(environment)
                        verify_phase5_append_only(project, environment)
                        if phase == 5:
                            verify_phase5_migration_cycle(project, environment)
                            print("Full Compose Phase 5 verification passed.")
                        else:
                            # Run the reversible cycle before Phase 6 creates additive Phase 4
                            # record types, whose downgrade guard intentionally fails closed.
                            verify_phase6_migration_cycle(project, environment)
                            verify_phase6_api(api_url)
                            verify_phase6_postgres_acceptance(environment)
                            verify_phase6_append_only(project, environment)
                            print("Full Compose Phase 6 verification passed.")
        else:
            run(
                [
                    "exec",
                    "-T",
                    "api",
                    "alembic",
                    "-c",
                    "services/api/alembic.ini",
                    "downgrade",
                    "base",
                ],
                project=project,
                env=environment,
            )
            run(
                [
                    "exec",
                    "-T",
                    "api",
                    "alembic",
                    "-c",
                    "services/api/alembic.ini",
                    "upgrade",
                    "head",
                ],
                project=project,
                env=environment,
            )
            print("Full Compose Phase 1 verification passed.")
    finally:
        subprocess.run(
            ["docker", "compose", "--project-name", project, "down", "--volumes"],
            cwd=ROOT,
            check=False,
            text=True,
            env=environment,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify phase-aware repository policy and services."
    )
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "--phase",
        type=phase_number,
        default=os.environ.get("FABLE5_VERIFY_PHASE", "6"),
        help=(
            "Apply repository policy checks for phase 1, 2, 3, 4, 5, or 6 "
            "(default: FABLE5_VERIFY_PHASE or 6)."
        ),
    )
    args = parser.parse_args()
    verify_static(args.phase)
    if not args.static_only:
        verify_compose(args.phase)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Repository verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
