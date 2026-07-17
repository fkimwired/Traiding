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
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
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
PHASE_7_REQUIRED_PATHS = (
    "docs/PHASE_07_APPROVAL_DECISIONS.md",
    "docs/handoffs/PHASE_08.md",
    "services/api/migrations/versions/0007_phase7_approval_risk.py",
    "services/api/src/fable5_api/approvals.py",
    "services/api/tests/test_phase7_openapi_contract.py",
    "services/api/tests/test_phase7_routes.py",
    "services/risk/src/fable5_risk/__init__.py",
    "services/risk/src/fable5_risk/canonical.py",
    "services/risk/src/fable5_risk/contracts.py",
    "services/risk/src/fable5_risk/fixtures.py",
    "services/risk/src/fable5_risk/repository.py",
    "services/risk/src/fable5_risk/workflow.py",
    "services/risk/tests/test_phase7_postgres.py",
    "services/risk/tests/test_phase7_workflow.py",
    "packages/contracts/src/phase7-contract.type-test.ts",
    "tests/test_phase7_migration.py",
    "tests/test_phase7_static.py",
)
PHASE_7_TABLES = (
    "approval_policies",
    "approval_scopes",
    "approval_authorizations",
    "approval_revocations",
    "approval_risk_inputs",
    "approval_assessments",
    "approval_checks",
)
PHASE_7_APPEND_ONLY_ERROR = "Phase 7 approval and risk artifacts are append-only"
PHASE_8_REQUIRED_PATHS = (
    "docs/PHASE_08_UI_DECISIONS.md",
    "packages/contracts/scripts/generate-runtime.mjs",
    "packages/contracts/src/runtime.generated.ts",
    "packages/contracts/src/validate-response.ts",
    "services/frontend/playwright.config.ts",
    "services/frontend/e2e/phase8.accessibility.spec.ts",
    "services/frontend/e2e/phase8.visual.spec.ts",
    "services/frontend/e2e/visual-stability.css",
    "services/frontend/src/app/ideas/IdeaIntakeWorkspace.tsx",
    "services/frontend/src/app/ideas/TradingIdeaCardView.tsx",
    "services/frontend/src/app/lineage/LineageExplorer.tsx",
    "services/frontend/src/app/lineage/page.tsx",
    "services/frontend/src/app/paper/PaperStatusWorkspace.tsx",
    "services/frontend/src/app/research/ResearchWorkspace.tsx",
    "services/frontend/src/app/risk/RiskComplianceWorkspace.tsx",
    "services/frontend/src/lib/api.ts",
    "services/frontend/src/lib/evidence-index.ts",
    "services/frontend/src/lib/navigation.ts",
)
PHASE_8_VISUAL_SNAPSHOT_DIRECTORY = "services/frontend/e2e/__screenshots__/phase8.visual.spec.ts"
PHASE_8_VISUAL_MODE_SLUGS = (
    "idea-intake",
    "research-lab",
    "simulated-paper-status",
    "risk-compliance",
)
PHASE_8_VISUAL_STATES = ("mode", "negative")
PHASE_8_VISUAL_PROJECTS = ("mobile", "tablet", "desktop")
PHASE_8_VISUAL_PLATFORMS = ("win32", "linux")
PHASE_8_VISUAL_BASELINES = frozenset(
    f"{mode}-{state}-{project}-{platform}.png"
    for mode in PHASE_8_VISUAL_MODE_SLUGS
    for state in PHASE_8_VISUAL_STATES
    for project in PHASE_8_VISUAL_PROJECTS
    for platform in PHASE_8_VISUAL_PLATFORMS
)
PHASE_8_TIMELINE_PATH = "/v1/approval-assessments/{assessment_id}/evidence-timeline"
PHASE_8_BASELINE_SHA = "94bcfaabf9de457aec47e49e332865a8dcc74f30"
EXPECTED_PHASE_8_TREE = "56d2cf38ba0ff3d5427fbf5f20aefa13d5224581"
PHASE_9_REQUIRED_PATHS = (
    "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
    "docs/handoffs/PHASE_09.md",
    "scripts/run_phase_gate.py",
    "tests/test_phase9_gate_runner.py",
    "tests/test_phase9_static.py",
)
PHASE_9_ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
        "docs/handoffs/PHASE_09.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/run_phase_gate.py",
        "scripts/verify_phase1.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_gate_runner.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }
)
PHASE_8_ACCESSIBILITY_SPEC = "services/frontend/e2e/phase8.accessibility.spec.ts"
PHASE_8_BROWSER_SPECS = (
    "e2e/phase8.accessibility.spec.ts",
    "e2e/phase8.visual.spec.ts",
)
PHASE_9_BROWSER_TIMEOUT_FLAG = "FABLE5_PHASE9_BROWSER_TIMEOUT_PROFILE"
PHASE_9_PLAYWRIGHT_VERSION = "1.61.1"
PHASE_9_PLAYWRIGHT_IMAGE_SHA256 = "5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48"
PHASE_9_LINUX_PLAYWRIGHT_IMAGE = (
    f"mcr.microsoft.com/playwright:v{PHASE_9_PLAYWRIGHT_VERSION}-noble@"
    f"sha256:{PHASE_9_PLAYWRIGHT_IMAGE_SHA256}"
)
PHASE_9_LINUX_PLAYWRIGHT_CONTAINER_SUFFIX = "_phase9_playwright"
PHASE_9_PLAYWRIGHT_RESULT_PREFIX = "FABLE5_PHASE9_PLAYWRIGHT_RESULT "
PHASE_9_PLAYWRIGHT_FAILURE_LOCATIONS = {
    "phase8.accessibility.spec.ts": {327, 361, 442, 514, 570, 666},
    "phase8.visual.spec.ts": {71},
}
PHASE_9_PLAYWRIGHT_TIMEOUTS = {
    ("phase8.accessibility.spec.ts", 570): 2_100_000,
    ("phase8.accessibility.spec.ts", 666): 420_000,
}
PHASE_8_LINEAGE_TIMEOUT_BASELINE = b"  test.setTimeout(1_200_000);"
PHASE_9_LINEAGE_TIMEOUT_REPLACEMENT = (
    b"  test.setTimeout(\n"
    b'    process.env.FABLE5_PHASE9_BROWSER_TIMEOUT_PROFILE === "1" ? '
    b"2_100_000 : 1_200_000,\n"
    b"  );"
)
PHASE_9_CONTRACT_SHA256 = {
    "packages/contracts/openapi.json": (
        "d89a72e31778ed7d6edcaaf5611e99506aecdc49c640df336e2a622023a0bb25"
    ),
    "packages/contracts/src/api.generated.ts": (
        "5fa0ce5d903529705709dc2dc0f4c86d71830fc634548551d145cf3bb7a0003e"
    ),
    "packages/contracts/src/runtime.generated.ts": (
        "905810491adf9f52090ff8af109137df76c76367293a21cd39a71dc643a4b964"
    ),
    "packages/contracts/src/validate-response.ts": (
        "57f74259a7d8f00bd739099a01eebd25d4fa7fed01d2e12320d28d67620e3503"
    ),
}
PHASE_9_IMMUTABLE_PREFIXES = (
    "services/extraction/tests/fixtures/",
    "services/data/src/fable5_data/fixtures/",
    f"{PHASE_8_VISUAL_SNAPSHOT_DIRECTORY}/",
)
PHASE_9_IMMUTABLE_ARTIFACTS = (
    "docs/PHASE_02_SCHEMA_DECISIONS.md",
    "docs/PHASE_03_MAPPING_DECISIONS.md",
    "docs/PHASE_04_DATA_DECISIONS.md",
    "docs/PHASE_06_RESEARCH_DECISIONS.md",
    "docs/PHASE_07_APPROVAL_DECISIONS.md",
    "docs/PHASE_08_UI_DECISIONS.md",
    "docs/handoffs/PHASE_02.md",
    "docs/handoffs/PHASE_03.md",
    "docs/handoffs/PHASE_04.md",
    "docs/handoffs/PHASE_07.md",
    "docs/handoffs/PHASE_08.md",
)
PHASE_9_BASELINE_SHA = "12a87e9dfb71afd7bb02d1f947ffea63be56a0a3"
EXPECTED_PHASE_9_TREE = "472792e0f53fc5c29ef8d4d73bdef60d6f25a1c9"
PHASE_10_REQUIRED_PATHS = (
    "docs/PHASE_10_LOCAL_PAPER_DECISIONS.md",
    "docs/handoffs/PHASE_10.md",
    "services/api/migrations/versions/0008_phase10_local_paper.py",
    "services/api/src/fable5_api/local_simulations.py",
    "services/api/tests/test_phase10_openapi_contract.py",
    "services/api/tests/test_phase10_browser_fixtures.py",
    "services/api/tests/test_phase10_routes.py",
    "services/frontend/e2e/fixtures/phase10-blocked-assessment.json",
    "services/frontend/e2e/fixtures/phase10-blocked.json",
    "services/frontend/e2e/fixtures/phase10-completed.json",
    "services/frontend/e2e/fixtures/phase10-source-assessment.json",
    "services/frontend/e2e/fixtures/phase10-synthetic-card.json",
    "services/frontend/e2e/phase10.fixtures.ts",
    "services/paper/README.md",
    "services/paper/src/fable5_paper/__init__.py",
    "services/paper/src/fable5_paper/canonical.py",
    "services/paper/src/fable5_paper/contracts.py",
    "services/paper/src/fable5_paper/fixtures.py",
    "services/paper/src/fable5_paper/repository.py",
    "services/paper/src/fable5_paper/workflow.py",
    "services/paper/tests/test_phase10_postgres.py",
    "services/paper/tests/test_phase10_workflow.py",
    "packages/contracts/src/phase10-contract.type-test.ts",
    "tests/test_phase10_migration.py",
    "tests/test_phase10_static.py",
)
PHASE_10_TABLES = (
    "paper_simulation_runs",
    "paper_simulation_checks",
    "paper_simulation_ledger_entries",
)
PHASE_10_CHECK_CODES = (
    "SOURCE_APPROVAL_EXACT",
    "TRANSITION_APPROVAL_FRESH",
    "RESEARCH_PREREQUISITES_COMPLETE",
    "SIMULATION_CONFIGURATION_EXACT",
    "RISK_CONTEXT_EXACT",
    "COST_SLIPPAGE_COMPLETE",
    "LOCAL_BOUNDARY_ENFORCED",
)
PHASE_10_APPEND_ONLY_ERROR = "Phase 10 local paper simulation artifacts are append-only"
PHASE_10_LINUX_SNAPSHOT_FLAG = "FABLE5_PHASE10_GENERATE_LINUX_SNAPSHOTS"
PHASE_10_VISUAL_SNAPSHOT_DIRECTORY = "services/frontend/e2e/__screenshots__/phase10.visual.spec.ts"
PHASE_10_VISUAL_STATES = ("completed", "blocked")
PHASE_10_VISUAL_PROJECTS = ("mobile", "tablet", "desktop")
PHASE_10_VISUAL_PLATFORMS = ("win32", "linux")
PHASE_10_VISUAL_BASELINES = frozenset(
    f"phase10-{state}-{project}-{platform}.png"
    for state in PHASE_10_VISUAL_STATES
    for project in PHASE_10_VISUAL_PROJECTS
    for platform in PHASE_10_VISUAL_PLATFORMS
)
PHASE_10_VISUAL_BASELINE_PATHS = frozenset(
    f"{PHASE_10_VISUAL_SNAPSHOT_DIRECTORY}/{name}" for name in PHASE_10_VISUAL_BASELINES
)
PHASE_10_PAPER_PATHS = frozenset(
    {
        "services/paper/README.md",
        "services/paper/src/fable5_paper/__init__.py",
        "services/paper/src/fable5_paper/canonical.py",
        "services/paper/src/fable5_paper/contracts.py",
        "services/paper/src/fable5_paper/fixtures.py",
        "services/paper/src/fable5_paper/repository.py",
        "services/paper/src/fable5_paper/workflow.py",
        "services/paper/tests/test_phase10_postgres.py",
        "services/paper/tests/test_phase10_workflow.py",
    }
)
PHASE_10_ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_10_LOCAL_PAPER_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_10.md",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/phase10-contract.type-test.ts",
        "packages/contracts/src/runtime.generated.ts",
        "pyproject.toml",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_phase1.py",
        "services/api/Dockerfile",
        "services/api/migrations/versions/0008_phase10_local_paper.py",
        "services/api/src/fable5_api/local_simulations.py",
        "services/api/src/fable5_api/main.py",
        "services/api/tests/test_phase10_openapi_contract.py",
        "services/api/tests/test_phase10_browser_fixtures.py",
        "services/api/tests/test_phase10_routes.py",
        "services/frontend/e2e/fixtures/phase10-blocked-assessment.json",
        "services/frontend/e2e/fixtures/phase10-blocked.json",
        "services/frontend/e2e/fixtures/phase10-completed.json",
        "services/frontend/e2e/fixtures/phase10-source-assessment.json",
        "services/frontend/e2e/fixtures/phase10-synthetic-card.json",
        "services/frontend/e2e/phase10.fixtures.ts",
        "services/frontend/e2e/phase10.accessibility.spec.ts",
        "services/frontend/e2e/phase10.visual.spec.ts",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "services/frontend/src/app/paper/PaperStatusWorkspace.tsx",
        "services/frontend/src/app/lineage/LineageExplorer.tsx",
        "services/frontend/src/app/phase8.css",
        "services/frontend/src/lib/api.ts",
        "services/frontend/src/tests/ApiClient.test.ts",
        "services/frontend/src/tests/PaperStatusWorkspace.test.tsx",
        "services/frontend/src/tests/Phase10Lineage.test.tsx",
        "services/jobs/Dockerfile",
        "tests/test_phase10_migration.py",
        "tests/test_phase10_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
        *PHASE_10_PAPER_PATHS,
        *PHASE_10_VISUAL_BASELINE_PATHS,
    }
)
PHASE_7_CHECK_CODES = (
    "RESEARCH_PASS",
    "PHASE6_LINEAGE_COMPLETE",
    "POLICY_CURRENT",
    "POLICY_MATCH",
    "SCOPE_CURRENT",
    "SCOPE_MATCH",
    "AUTHORIZATION_CURRENT",
    "AUTHORIZATION_MATCH",
    "REVOCATION_CLEAR",
    "RISK_INPUT_FRESH",
    "GLOBAL_CONTROL_CLEAR",
    "STRATEGY_CONTROL_CLEAR",
    "DATA_QUALITY_CONTROL_CLEAR",
    "MARKET_CALENDAR_OPEN",
    "DUPLICATE_CONTEXT_CLEAR",
    "NOTIONAL_LIMIT",
    "GROSS_EXPOSURE_LIMIT",
    "NET_EXPOSURE_LIMIT",
    "SECTOR_EXPOSURE_LIMIT",
    "CONCENTRATION_LIMIT",
    "LIQUIDITY_MINIMUM",
    "TURNOVER_LIMIT",
    "VOLATILITY_LIMIT",
    "DAILY_LOSS_LIMIT",
    "DRAWDOWN_LIMIT",
)
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
PHASE_6_DETAIL_TIMEOUT_SECONDS = 60
PHASE_6_VALIDATION_TIMEOUT_SECONDS = 10
PHASE_9_PHASE6_REQUEST_TIMEOUT_SECONDS = 480
PHASE_9_PHASE6_DETAIL_TIMEOUT_SECONDS = 180
PHASE_9_PHASE6_VALIDATION_TIMEOUT_SECONDS = 30
PHASE_6_TIMEOUT_PHASE: ContextVar[int] = ContextVar("phase6_timeout_phase", default=6)
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
PHASE_1_6_MIGRATION_SHA256 = {
    **PHASE_1_5_MIGRATION_SHA256,
    "services/api/migrations/versions/0006_phase6_research.py": (
        "7f4ab516a31208b7c5f5400b1b593d7675c75570fa839f524bfddea3152d7070"
    ),
}
PHASE_1_7_MIGRATION_SHA256 = {
    **PHASE_1_6_MIGRATION_SHA256,
    "services/api/migrations/versions/0007_phase7_approval_risk.py": (
        "4ef4e6301f205fb9a18f478ac3fa6d6920dbe0af462b6f371e83dd2d622a8090"
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
        raise argparse.ArgumentTypeError("phase must be 1, 2, 3, 4, 5, 6, 7, 8, 9, or 10") from exc
    if phase not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
        raise argparse.ArgumentTypeError("phase must be 1, 2, 3, 4, 5, 6, 7, 8, 9, or 10")
    return phase


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@contextmanager
def phase9_stage(phase: int, stage: str) -> Iterator[None]:
    if phase != 9:
        yield
        return
    started_at = utc_now()
    started = time.monotonic()
    result = "pass"
    try:
        yield
    except BaseException:
        result = "fail"
        raise
    finally:
        marker = {
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "end_utc": utc_now(),
            "result": result,
            "stage": stage,
            "start_utc": started_at,
        }
        print(
            "FABLE5_PHASE9_STAGE "
            + json.dumps(marker, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            flush=True,
        )


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


def verify_static_inherited(phase: int = 1, *, announce: bool = True) -> None:
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
    if phase >= 7:
        missing_phase7 = [path for path in PHASE_7_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase7:
            raise AssertionError(f"Missing Phase 7 paths: {', '.join(missing_phase7)}")
    if phase >= 8:
        missing_phase8 = [path for path in PHASE_8_REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing_phase8:
            raise AssertionError(f"Missing Phase 8 paths: {', '.join(missing_phase8)}")

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
        ci_phases = [int(value) for value in re.findall(r"--phase\s+(10|[1-9])\b", ci)]
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
        dormant_directories = ["strategy_specs"]
        if phase < 7:
            dormant_directories.append("services/risk")
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
            PHASE_1_7_MIGRATION_SHA256
            if phase >= 8
            else PHASE_1_6_MIGRATION_SHA256
            if phase >= 7
            else PHASE_1_5_MIGRATION_SHA256
            if phase >= 6
            else PHASE_1_4_MIGRATION_SHA256
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
            if phase < 7 and any(term in path.casefold() for term in PHASE_4_FORBIDDEN_API_TERMS):
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
        if phase < 7:
            for path in openapi["paths"]:
                if any(term in path.casefold() for term in forbidden_later_phase_paths):
                    raise AssertionError(
                        f"Phase 6/7 capability leaked into the Phase 5 API: {path}"
                    )

        phase5_surfaces: tuple[Path, ...] = (
            ROOT / "services/api/src/fable5_api/evaluations.py",
            ROOT / "services/api/migrations/versions/0005_phase5_evaluation.py",
        )
        phase5_surfaces += tuple(backtester_root.rglob("*.py"))
        if phase < 7:
            phase5_surfaces += (
                ROOT / "packages/contracts/openapi.json",
                ROOT / "packages/contracts/src/api.generated.ts",
            )
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
            "risk_override",
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
        if phase < 7:
            for path in domain_paths:
                if any(term in path.casefold() for term in forbidden_phase7_paths):
                    raise AssertionError(
                        f"Phase 7 or execution capability leaked into Phase 6: {path}"
                    )
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

    if phase >= 7:
        migration = normalized(
            ROOT / "services/api/migrations/versions/0007_phase7_approval_risk.py"
        )
        if (
            'revision: str = "0007_phase7"' not in migration
            or 'down_revision: str | None = "0006_phase6"' not in migration
            or PHASE_7_APPEND_ONLY_ERROR not in migration
            or "DEFERRABLE INITIALLY DEFERRED" not in migration
        ):
            raise AssertionError("Phase 7 migration authority or deferred completeness is missing")
        for table in PHASE_7_TABLES:
            evidence = f'op.create_table(\n        "{table}"'
            if evidence not in migration:
                raise AssertionError(f"Phase 7 migration is missing {table} evidence: {evidence}")
        for trigger_template in (
            "CREATE TRIGGER {table}_immutable",
            "CREATE TRIGGER {table}_no_truncate",
        ):
            if trigger_template not in migration:
                raise AssertionError(
                    f"Phase 7 migration is missing append-only trigger: {trigger_template}"
                )

        risk_root = ROOT / "services/risk/src/fable5_risk"
        forbidden_import_roots = {
            "aiohttp",
            "alpaca",
            "alpaca_py",
            "alpaca_trade_api",
            "ccxt",
            "httpx",
            "ib_insync",
            "ibapi",
            "requests",
            "socket",
            "urllib3",
        }
        for path in risk_root.rglob("*.py"):
            forbidden = imported_module_roots(path) & forbidden_import_roots
            if forbidden:
                raise AssertionError(
                    f"Phase 7 risk domain imports a vendor/network module: {path} {forbidden}"
                )
        workflow = normalized(risk_root / "workflow.py")
        if (
            "PromotionState.PASS_RESEARCH" not in workflow
            or "ApprovalCheckCode.RESEARCH_PASS" not in workflow
            or "phase6-a-pass-v2" in workflow
            or "-pass-" in workflow
        ):
            raise AssertionError(
                "Phase 7 eligibility must derive only from immutable Phase 6 promotion state"
            )
        approvals_api = normalized(ROOT / "services/api/src/fable5_api/approvals.py")
        if (
            "phase7_code_version_git_sha=settings.code_version_git_sha" not in approvals_api
            or "SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA" in approvals_api
            or "phase7_code_version_git_sha_missing" not in workflow
        ):
            raise AssertionError("Phase 7 must fail closed instead of fabricating a git SHA")
        for boundary in (
            "execution_authorized: Literal[False]",
            "execution_ready: Literal[False]",
            "simulated_paper_only: Literal[True]",
            "no_personalized_investment_advice: Literal[True]",
            "no_real_performance_claimed: Literal[True]",
        ):
            if boundary not in normalized(risk_root / "contracts.py"):
                raise AssertionError(f"Phase 7 contract safety boundary is missing: {boundary}")

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        components = openapi["components"]["schemas"]
        phase7_methods = {"get", "post", "put", "patch", "delete"}
        phase7_path_terms = (
            "approval",
            "authorization",
            "revocation",
            "risk",
            "governance",
            "pre-order",
            "pre_order",
        )
        expected_phase7_paths = {
            "/v1/approval-assessments": {"get", "post"},
            "/v1/approval-assessments/{assessment_id}": {"get"},
            PHASE_8_TIMELINE_PATH: {"get"},
            "/v1/approval-revocations": {"get", "post"},
            "/v1/approval-revocations/{revocation_id}": {"get"},
        }
        phase7_paths: dict[str, set[str]] = {}
        for path, operations in openapi["paths"].items():
            methods = set(operations) & phase7_methods
            tags = {
                tag
                for method, operation in operations.items()
                if method in phase7_methods and isinstance(operation, dict)
                for tag in operation.get("tags", [])
            }
            if (
                path in expected_phase7_paths
                or "approval-governance" in tags
                or any(term in path.casefold() for term in phase7_path_terms)
            ):
                phase7_paths[path] = methods
        if phase7_paths != expected_phase7_paths:
            raise AssertionError(
                f"Phase 7 approval/governance/risk paths and methods are not exact: {phase7_paths}"
            )
        expected_components = {
            "ApprovalAssessmentArtifact",
            "ApprovalAssessmentCreateRequest",
            "ApprovalAssessmentEvidenceTimeline",
            "ApprovalAssessmentSummary",
            "ApprovalPolicyTimelineEvidence",
            "ApprovalRiskInputTimelineEvidence",
            "ApprovalScopeTimelineEvidence",
            "ApprovalRevocationCreateRequest",
            "ApprovalValidationErrorResponse",
            "AuthorizationRevocationArtifact",
            "AuthorizationRevocationSummary",
            "HumanAuthorizationTimelineEvidence",
        }
        missing_components = expected_components - set(components)
        if missing_components:
            raise AssertionError(
                f"Phase 7 OpenAPI is missing schemas: {sorted(missing_components)}"
            )
        exact_request_fields = {
            "ApprovalAssessmentCreateRequest": {
                "research_run_id",
                "approval_policy_version_id",
                "approval_scope_version_id",
                "human_authorization_evidence_id",
                "risk_input_id",
            },
            "ApprovalRevocationCreateRequest": {
                "human_authorization_evidence_id",
                "revocation_evidence_id",
            },
        }
        for schema_name, expected_fields in exact_request_fields.items():
            request_schema = components[schema_name]
            if (
                set(request_schema.get("properties", {})) != expected_fields
                or set(request_schema.get("required", [])) != expected_fields
                or request_schema.get("additionalProperties") is not False
            ):
                raise AssertionError(
                    f"{schema_name} accepts client-authoritative Phase 7 evidence or outcomes"
                )
        artifact_properties = components["ApprovalAssessmentArtifact"].get("properties", {})
        expected_constants = {
            "synthetic": True,
            "simulated_paper_only": True,
            "execution_authorized": False,
            "execution_ready": False,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
        }
        for field, expected in expected_constants.items():
            if artifact_properties.get(field, {}).get("const") is not expected:
                raise AssertionError(f"Phase 7 artifact safety flag is not constant: {field}")
        for path, operations in openapi["paths"].items():
            methods = {
                method
                for method in operations
                if method in {"get", "post", "put", "patch", "delete"}
            }
            if methods - {"get", "post"}:
                raise AssertionError(f"Phase 7 API exposes a mutation method: {path} {methods}")
            if path.startswith("/v1/") and any(
                token in path.casefold()
                for token in (
                    "broker",
                    "fill",
                    "position",
                    "orders",
                    "submission",
                    "paper-execution",
                    "paper_execution",
                    "live",
                )
            ):
                raise AssertionError(f"Execution capability leaked into Phase 7 API: {path}")

        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        for generated_contract in (
            "ApprovalAssessmentArtifact:",
            "ApprovalAssessmentCreateRequest:",
            "ApprovalAssessmentEvidenceTimeline:",
            "ApprovalAssessmentSummary:",
            "ApprovalRevocationCreateRequest:",
            "AuthorizationRevocationArtifact:",
            "AuthorizationRevocationSummary:",
            '"/v1/approval-assessments"',
            f'"{PHASE_8_TIMELINE_PATH}"',
            '"/v1/approval-revocations"',
        ):
            if generated_contract not in generated:
                raise AssertionError(
                    f"Generated TypeScript Phase 7 contract is missing {generated_contract}"
                )

    if phase >= 8:
        migration_root = ROOT / "services/api/migrations/versions"
        forbidden_migrations = (
            sorted(path.name for path in migration_root.glob("0008*.py")) if phase == 8 else []
        )
        if forbidden_migrations:
            raise AssertionError(
                "Phase 8 must not add a database migration: " + ", ".join(forbidden_migrations)
            )

        openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
        paths = openapi["paths"]
        components = openapi["components"]["schemas"]
        if PHASE_8_TIMELINE_PATH not in paths:
            raise AssertionError("Phase 8 evidence-timeline GET is missing")
        timeline_operations = paths[PHASE_8_TIMELINE_PATH]
        if set(timeline_operations) != {"get"}:
            raise AssertionError(
                f"Phase 8 evidence timeline must be GET-only: {sorted(timeline_operations)}"
            )
        timeline_get = timeline_operations["get"]
        if "requestBody" in timeline_get:
            raise AssertionError("Phase 8 evidence timeline must not accept a request body")
        if timeline_get.get("parameters") != [
            {
                "in": "path",
                "name": "assessment_id",
                "required": True,
                "schema": {
                    "format": "uuid",
                    "title": "Assessment Id",
                    "type": "string",
                },
            }
        ]:
            raise AssertionError(
                "Phase 8 evidence timeline accepts presentation authority beyond assessment_id"
            )
        response_schema = (
            timeline_get.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema")
        )
        if response_schema != {"$ref": "#/components/schemas/ApprovalAssessmentEvidenceTimeline"}:
            raise AssertionError("Phase 8 evidence timeline response is not server-owned")

        expected_timeline_fields = {
            "ApprovalAssessmentEvidenceTimeline": {
                "assessment_id",
                "assessment_created_at_utc",
                "policy",
                "scope",
                "authorization",
                "risk_input",
            },
            "ApprovalPolicyTimelineEvidence": {
                "approval_policy_version_id",
                "policy_sha256",
                "valid_from_utc",
                "expires_at_utc",
            },
            "ApprovalScopeTimelineEvidence": {
                "approval_scope_version_id",
                "scope_sha256",
                "valid_from_utc",
                "expires_at_utc",
            },
            "HumanAuthorizationTimelineEvidence": {
                "human_authorization_evidence_id",
                "authorization_sha256",
                "authorized_at_utc",
                "review_at_utc",
                "expires_at_utc",
            },
            "ApprovalRiskInputTimelineEvidence": {
                "risk_input_id",
                "risk_input_sha256",
                "observed_at_utc",
            },
        }
        for schema_name, expected_fields in expected_timeline_fields.items():
            schema = components.get(schema_name, {})
            if (
                set(schema.get("properties", {})) != expected_fields
                or set(schema.get("required", [])) != expected_fields
                or schema.get("additionalProperties") is not False
            ):
                raise AssertionError(
                    f"{schema_name} exposes fields beyond existing identifier/hash/time evidence"
                )
        nested_refs = {
            "policy": "ApprovalPolicyTimelineEvidence",
            "scope": "ApprovalScopeTimelineEvidence",
            "authorization": "HumanAuthorizationTimelineEvidence",
            "risk_input": "ApprovalRiskInputTimelineEvidence",
        }
        timeline_properties = components["ApprovalAssessmentEvidenceTimeline"]["properties"]
        for field, schema_name in nested_refs.items():
            if timeline_properties[field] != {"$ref": f"#/components/schemas/{schema_name}"}:
                raise AssertionError(f"Phase 8 timeline {field} is not a generated strict model")

        api_paths = {path.casefold() for path in paths if path.startswith("/v1/")}
        if any(
            "research-audit" in path
            or "research_audit" in path
            or "audit-events" in path
            or "audit_events" in path
            for path in api_paths
        ):
            raise AssertionError("Phase 8 exposed the unrelated research_audit_events table")
        forbidden_execution_terms = (
            "broker",
            "submission",
            "fill",
            "position",
            "order",
            "executable-paper",
            "executable_paper",
            "paper-execution",
            "paper_execution",
            "live",
        )
        for path in api_paths:
            if any(term in path for term in forbidden_execution_terms):
                raise AssertionError(f"Execution-shaped API leaked into Phase 8: {path}")

        generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
        for contract in (
            "ApprovalAssessmentEvidenceTimeline:",
            "ApprovalPolicyTimelineEvidence:",
            "ApprovalRiskInputTimelineEvidence:",
            "ApprovalScopeTimelineEvidence:",
            "HumanAuthorizationTimelineEvidence:",
            f'"{PHASE_8_TIMELINE_PATH}"',
        ):
            if contract not in generated:
                raise AssertionError(f"Generated Phase 8 TypeScript contract is missing {contract}")

        api_client = normalized(ROOT / "services/frontend/src/lib/api.ts")
        if (
            'from "@fable5/contracts"' not in api_client
            or 'components["schemas"]' not in api_client
            or "paths[" not in api_client
            or "getApprovalAssessmentEvidenceTimeline" not in api_client
            or "validateOpenApiResponse(operation, response.status, body)" not in api_client
            or "SuccessfulJsonOperation" not in api_client
            or "SuccessfulJsonResponseByOperation[Operation]" not in api_client
            or "operationRequest(operation, options.pathParameters)" not in api_client
            or re.search(
                r"(?:getJson|postJson)<",
                api_client.split("export const fable5Api =", maxsplit=1)[-1],
            )
            or "expectArray" in api_client
            or "validate?:" in api_client
        ):
            raise AssertionError("Phase 8 client is not derived from generated contracts")

        runtime_generated = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
        runtime_values: dict[str, list[str]] = {}
        for constant_name, schema_name in (
            ("sourceTypes", "SourceType"),
            ("sourceAuthorities", "SourceAuthority"),
        ):
            match = re.search(
                rf"export const {constant_name} = (\[.*?\]) as const;",
                runtime_generated,
                flags=re.DOTALL,
            )
            if match is None:
                raise AssertionError(f"Generated runtime contract is missing {constant_name}")
            values = json.loads(match.group(1))
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise AssertionError(f"Generated runtime contract {constant_name} is malformed")
            if values != components[schema_name].get("enum"):
                raise AssertionError(
                    f"Generated runtime contract {constant_name} drifted from {schema_name}"
                )
            runtime_values[constant_name] = values
        user_intake_match = re.search(
            r"export const userIntakeSourceTypes = (\[.*?\]) as const;",
            runtime_generated,
            flags=re.DOTALL,
        )
        if user_intake_match is None:
            raise AssertionError("Generated runtime contract is missing userIntakeSourceTypes")
        user_intake_source_types = json.loads(user_intake_match.group(1))
        source_types = runtime_values["sourceTypes"]
        if source_types.count("synthetic_fixture") != 1:
            raise AssertionError(
                "OpenAPI SourceType must contain exactly one reserved synthetic_fixture value"
            )
        expected_user_intake_source_types = [
            value for value in source_types if value != "synthetic_fixture"
        ]
        if (
            user_intake_source_types != expected_user_intake_source_types
            or "synthetic_fixture" in user_intake_source_types
        ):
            raise AssertionError(
                "Generated user intake source types did not preserve full OpenAPI parity while "
                "excluding synthetic_fixture"
            )
        operations_match = re.search(
            r"export const successfulJsonOperations = (\[.*?\]) as const;",
            runtime_generated,
            flags=re.DOTALL,
        )
        if operations_match is None:
            raise AssertionError("Generated runtime response operations are missing")
        runtime_operations = json.loads(operations_match.group(1))
        expected_runtime_operations = []
        for path, path_item in sorted(paths.items()):
            for method, operation in sorted(path_item.items()):
                if method not in {"delete", "get", "patch", "post", "put"}:
                    continue
                responses = operation.get("responses", {})
                if any(
                    re.fullmatch(r"2\d\d", status)
                    and response.get("content", {}).get("application/json", {}).get("schema")
                    for status, response in responses.items()
                ):
                    expected_runtime_operations.append(f"{method.upper()} {path}")
        if runtime_operations != expected_runtime_operations:
            raise AssertionError(
                "Generated runtime response operations drifted from successful OpenAPI responses"
            )
        if (
            'import type { paths } from "./api.generated";' not in runtime_generated
            or "export type SuccessfulJsonResponseByOperation = {" not in runtime_generated
        ):
            raise AssertionError(
                "Generated operation keys are not type-bound to their OpenAPI success responses"
            )
        client_operations = set(re.findall(r'"((?:GET|POST) /[^"\r\n]+)"', api_client))
        expected_client_operations = set(runtime_operations) - {"GET /ready"}
        if client_operations != expected_client_operations:
            raise AssertionError(
                "Typed client runtime validation does not cover every generated API operation"
            )
        contracts_index = normalized(ROOT / "packages/contracts/src/index.ts")
        runtime_export = re.search(
            r'export\s*\{(?P<names>.*?)\}\s*from\s*"\./runtime\.generated";',
            contracts_index,
            flags=re.DOTALL,
        )
        exported_runtime_names = (
            {name.strip() for name in runtime_export.group("names").split(",") if name.strip()}
            if runtime_export
            else set()
        )
        if exported_runtime_names != {
            "sourceAuthorities",
            "sourceTypes",
            "userIntakeSourceTypes",
        }:
            raise AssertionError("Generated runtime enum values are not exported by contracts")
        if (
            'export type { SuccessfulJsonResponseByOperation } from "./runtime.generated";'
            not in contracts_index
        ):
            raise AssertionError("Generated operation response bindings are not exported")
        runtime_generator = normalized(ROOT / "packages/contracts/scripts/generate-runtime.mjs")
        runtime_validator = normalized(ROOT / "packages/contracts/src/validate-response.ts")
        generated_check = normalized(ROOT / "packages/contracts/scripts/check-generated.mjs")
        if (
            'enumValues("SourceType")' not in runtime_generator
            or 'enumValues("SourceAuthority")' not in runtime_generator
            or 'value !== "synthetic_fixture"' not in runtime_generator
            or "sourceTypes.length - 1" not in runtime_generator
            or "successfulJsonResponseSchemas" not in runtime_generator
            or "successfulJsonResponseTypeEntries" not in runtime_generator
            or "runtimeComponentSchemas" not in runtime_generator
            or "runtime.generated.ts" not in generated_check
            or "generate-runtime.mjs" not in generated_check
            or "validateOpenApiResponse" not in runtime_validator
            or "successfulJsonResponseSchemas" not in runtime_validator
            or "runtimeComponentSchemas" not in runtime_validator
            or "isValidCalendarDate" not in runtime_validator
            or "Array.from(value).length" not in runtime_validator
            or 'from "./validate-response"' not in contracts_index
        ):
            raise AssertionError(
                "Runtime enum/response generation is not covered by contract parity checks"
            )
        api_client_tests = normalized(ROOT / "services/frontend/src/tests/ApiClient.test.ts")
        if (
            "malformed collection members, detail artifacts, and evidence timelines"
            not in api_client_tests
            or "malformedMember" not in api_client_tests
            or "malformedDetail" not in api_client_tests
            or "malformedTimeline" not in api_client_tests
        ):
            raise AssertionError("Generated runtime response validation tests are incomplete")
        intake = normalized(ROOT / "services/frontend/src/app/ideas/IdeaIntakeWorkspace.tsx")
        contract_import = re.search(
            r'import\s*\{(?P<names>.*?)\}\s*from\s*"@fable5/contracts";',
            intake,
            flags=re.DOTALL,
        )
        imported_contract_names = (
            {
                name.removeprefix("type ").strip()
                for name in contract_import.group("names").split(",")
                if name.strip()
            }
            if contract_import
            else set()
        )
        if (
            not {"sourceAuthorities", "userIntakeSourceTypes"}.issubset(imported_contract_names)
            or "sourceTypes" in imported_contract_names
            or re.search(r"const\s+source(?:Types|Authorities)\s*=", intake) is not None
            or re.search(r"[\"']synthetic_fixture[\"']", intake) is not None
        ):
            raise AssertionError(
                "Idea Intake duplicates or bypasses the generated server-owned runtime enum"
            )
        frontend_production = tuple(
            path
            for path in (ROOT / "services/frontend/src").rglob("*.ts*")
            if "tests" not in path.parts
        )
        clock_authority_patterns = ("Date.now(", "new Date(", "performance.now(")
        for path in frontend_production:
            body = path.read_text(encoding="utf-8")
            if any(pattern in body for pattern in clock_authority_patterns):
                raise AssertionError(
                    "Phase 8 client compares historical governance evidence with a client clock: "
                    f"{path.relative_to(ROOT)}"
                )

        layout = normalized(ROOT / "services/frontend/src/app/layout.tsx")
        styles = normalized(ROOT / "services/frontend/src/app/phase8.css")
        if (
            'href="#main-content"' not in layout
            or 'id="main-content"' not in layout
            or ":focus-visible" not in styles
            or "prefers-reduced-motion: reduce" not in styles
        ):
            raise AssertionError(
                "Phase 8 keyboard, focus, landmark, or reduced-motion hooks are missing"
            )
        playwright = normalized(ROOT / "services/frontend/playwright.config.ts")
        for viewport in (
            "width: 390, height: 844",
            "width: 820, height: 1_180",
            "width: 1_440, height: 1_000",
        ):
            if viewport not in playwright:
                raise AssertionError(f"Phase 8 pinned visual viewport is missing: {viewport}")
        visual_spec = normalized(ROOT / "services/frontend/e2e/phase8.visual.spec.ts")
        accessibility_spec = normalized(ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts")
        paper_workspace = normalized(
            ROOT / "services/frontend/src/app/paper/PaperStatusWorkspace.tsx"
        )
        if phase == 8 and re.search(
            r"<(?:form|input|select|textarea)\b|type=\"submit\"", paper_workspace
        ):
            raise AssertionError("Simulated Paper Status exposed an executable-shaped control")
        for forbidden_paper_token in (
            "execution_authorized",
            "execution_ready",
            "order ticket",
            "paper execution",
            "paper_execution",
        ):
            if forbidden_paper_token in paper_workspace.casefold():
                raise AssertionError(
                    "Simulated Paper Status exposed an execution-readiness token: "
                    f"{forbidden_paper_token}"
                )
        if (
            "stylePath: stabilityStyles" not in visual_spec
            or 'page.locator("pre")' not in visual_spec
            or 'page.locator("blockquote")' not in visual_spec
            or "fullPage: false" not in visual_spec
            or "${mode.slug}-mode.png" not in visual_spec
            or "${mode.slug}-negative.png" not in visual_spec
            or 'block: "center"' not in visual_spec
            or "request timed out before deterministic evidence was available|could not be reached"
            not in visual_spec
            or "request timed out before deterministic evidence was available|could not be reached"
            not in accessibility_spec
            or "data-visual-corpus='synthetic'" not in visual_spec
            or "new AxeBuilder" not in accessibility_spec
            or "Skip to main content" not in accessibility_spec
            or "a[href^='/lineage?']" not in accessibility_spec
            or "Loading immutable evidence" not in accessibility_spec
            or "Referenced result was not found" not in accessibility_spec
            or "syntheticFixtureArchetypes" not in accessibility_spec
        ):
            raise AssertionError(
                "Phase 8 visual secrecy, accessibility, keyboard, or lineage QA is incomplete"
            )
        visual_snapshot_directory = ROOT / PHASE_8_VISUAL_SNAPSHOT_DIRECTORY
        actual_visual_baselines = (
            {path.name for path in visual_snapshot_directory.glob("*.png")}
            if visual_snapshot_directory.is_dir()
            else set()
        )
        missing_visual_baselines = sorted(PHASE_8_VISUAL_BASELINES - actual_visual_baselines)
        unexpected_visual_baselines = sorted(actual_visual_baselines - PHASE_8_VISUAL_BASELINES)
        if missing_visual_baselines or unexpected_visual_baselines:
            details = []
            if missing_visual_baselines:
                details.append(f"missing: {', '.join(missing_visual_baselines)}")
            if unexpected_visual_baselines:
                details.append(f"unexpected: {', '.join(unexpected_visual_baselines)}")
            raise AssertionError(
                "Phase 8 visual baselines are not the exact deterministic 48-file matrix ("
                + "; ".join(details)
                + ")"
            )
        for browser_guard in (
            'trace: "off"',
            "workers: 1",
            "FABLE5_UPDATE_SNAPSHOTS",
            "FABLE5_VISUAL_CORPUS",
            "127.0.0.1",
            "localhost",
            "host.docker.internal",
            "./.next/playwright-results",
        ):
            if browser_guard not in playwright:
                raise AssertionError(
                    f"Phase 8 browser safety configuration is missing {browser_guard}"
                )

        workflow_tests = normalized(ROOT / "services/risk/tests/test_phase7_workflow.py")
        route_tests = normalized(ROOT / "services/api/tests/test_phase7_routes.py")
        phase5_postgres_tests = normalized(ROOT / "tests/test_phase5_postgres.py")
        if '"8": "0007_phase7"' not in phase5_postgres_tests:
            raise AssertionError(
                "Phase 8 isolated PostgreSQL acceptance does not preserve the Phase 7 head"
            )
        if (
            "test_assessment_evidence_timeline_fails_closed_on_each_missing_reference"
            not in workflow_tests
            or "test_assessment_evidence_timeline_rejects_each_invalid_canonical_hash"
            not in workflow_tests
            or "test_assessment_evidence_timeline_rejects_each_wrong_identity_and_hash"
            not in workflow_tests
            or "conflicting_timeline.status_code == 409" not in route_tests
            or "missing_timeline.status_code == 404" not in route_tests
            or "test_each_timeline_evidence_reference_failure_is_sanitized" not in route_tests
        ):
            raise AssertionError("Phase 8 timeline 404/409 fail-closed tests are missing")

    if announce:
        print(f"Static repository policy checks passed for Phase {phase}.")


def git_text(*arguments: str) -> str:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssertionError(f"Git command failed: git {' '.join(arguments)}") from exc


def phase10_clean_git_identity(
    stage: str,
    *,
    expected: tuple[str, str] | None = None,
) -> tuple[str, str]:
    status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise AssertionError(f"Phase 10 {stage} requires a clean worktree and index: {status!r}")
    identity = (
        git_text("rev-parse", "--verify", "HEAD"),
        git_text("show", "-s", "--format=%T", "HEAD"),
    )
    sha, tree = identity
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None or re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise AssertionError(f"Phase 10 {stage} returned an invalid Git identity: {identity!r}")
    if expected is not None and identity != expected:
        raise AssertionError(
            f"Phase 10 Git identity changed during acceptance: expected={expected!r}, "
            f"actual={identity!r}"
        )
    print(f"Phase 10 acceptance identity ({stage}): sha={sha} tree={tree} clean=true")
    return identity


def git_blob(revision: str, path: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssertionError(f"Missing immutable baseline blob: {revision}:{path}") from exc


def verify_phase9_static() -> None:
    missing = [path for path in PHASE_9_REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Phase 9 paths: {', '.join(missing)}")

    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{PHASE_8_BASELINE_SHA}^{{commit}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssertionError("The exact Phase 8 baseline is unavailable in local history") from exc
    if git_text("show", "-s", "--format=%T", PHASE_8_BASELINE_SHA) != EXPECTED_PHASE_8_TREE:
        raise AssertionError("The authorized Phase 8 baseline tree does not match")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE_8_BASELINE_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise AssertionError("Phase 9 HEAD is not descended from the exact Phase 8 baseline")

    changed_paths = {
        path.replace("\\", "/")
        for path in git_text("diff", "--name-only", PHASE_8_BASELINE_SHA, "--").splitlines()
        if path
    }
    changed_paths.update(
        path.replace("\\", "/")
        for path in git_text("diff", "--cached", "--name-only", "--").splitlines()
        if path
    )
    changed_paths.update(
        path.replace("\\", "/")
        for path in git_text("ls-files", "--others", "--exclude-standard", "--").splitlines()
        if path
    )
    forbidden_changes = sorted(changed_paths - PHASE_9_ALLOWED_WRITES)
    if forbidden_changes:
        raise AssertionError(
            "Phase 9 changed paths outside the exact allowlist: " + ", ".join(forbidden_changes)
        )

    phase8_accessibility_baseline = git_blob(PHASE_8_BASELINE_SHA, PHASE_8_ACCESSIBILITY_SPEC)
    if phase8_accessibility_baseline.count(PHASE_8_LINEAGE_TIMEOUT_BASELINE) != 1:
        raise AssertionError("Phase 8 exhaustive-lineage timeout baseline is not unique")
    expected_phase9_accessibility = phase8_accessibility_baseline.replace(
        PHASE_8_LINEAGE_TIMEOUT_BASELINE,
        PHASE_9_LINEAGE_TIMEOUT_REPLACEMENT,
        1,
    )
    if (ROOT / PHASE_8_ACCESSIBILITY_SPEC).read_bytes() != expected_phase9_accessibility:
        raise AssertionError(
            "Phase 9 accessibility-spec drift exceeds the exact timeout-only exception"
        )

    migration_root = ROOT / "services/api/migrations/versions"
    migration_paths = {path.relative_to(ROOT).as_posix() for path in migration_root.glob("*.py")}
    if migration_paths != set(PHASE_1_7_MIGRATION_SHA256):
        raise AssertionError(
            "Phase 9 must retain exactly migrations 0001 through 0007 with head 0007_phase7"
        )
    if any(path.name.startswith("0008") for path in migration_root.glob("*.py")):
        raise AssertionError("Phase 9 must not add migration 0008")

    baseline_paths = set(
        git_text("ls-tree", "-r", "--name-only", PHASE_8_BASELINE_SHA).splitlines()
    )
    immutable_paths = (
        set(PHASE_9_CONTRACT_SHA256)
        | set(PHASE_1_7_MIGRATION_SHA256)
        | set(PHASE_9_IMMUTABLE_ARTIFACTS)
    )
    immutable_paths.update(
        path for path in baseline_paths if path.startswith(PHASE_9_IMMUTABLE_PREFIXES)
    )
    for path in sorted(immutable_paths):
        current = (ROOT / path).read_bytes()
        if current != git_blob(PHASE_8_BASELINE_SHA, path):
            raise AssertionError(f"Phase 9 immutable artifact drifted from Phase 8: {path}")

    for path, expected_sha256 in PHASE_9_CONTRACT_SHA256.items():
        actual_sha256 = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise AssertionError(f"Phase 9 contract hash changed for {path}: {actual_sha256}")
    for path, expected_sha256 in PHASE_1_7_MIGRATION_SHA256.items():
        actual_sha256 = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise AssertionError(f"Phase 9 migration hash changed for {path}: {actual_sha256}")

    visual_snapshot_directory = ROOT / PHASE_8_VISUAL_SNAPSHOT_DIRECTORY
    actual_visual_baselines = {path.name for path in visual_snapshot_directory.glob("*.png")}
    if actual_visual_baselines != PHASE_8_VISUAL_BASELINES:
        raise AssertionError("Phase 9 must retain the exact 48-file Phase 8 snapshot matrix")
    for target_platform in PHASE_8_VISUAL_PLATFORMS:
        platform_snapshots = {
            name for name in actual_visual_baselines if name.endswith(f"-{target_platform}.png")
        }
        if len(platform_snapshots) != 24:
            raise AssertionError(f"Phase 9 requires exactly 24 {target_platform} visual baselines")

    playwright = normalized(ROOT / "services/frontend/playwright.config.ts")
    for serial_guard in ("fullyParallel: false", "retries: 0", "workers: 1"):
        if serial_guard not in playwright:
            raise AssertionError(f"Phase 9 browser serialization drifted: {serial_guard}")
    package_lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    if (
        package_lock["packages"]["node_modules/@playwright/test"]["version"]
        != PHASE_9_PLAYWRIGHT_VERSION
    ):
        raise AssertionError("Phase 9 Linux browser image and Playwright package versions differ")
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    if "npx playwright install --with-deps chromium" in workflow:
        raise AssertionError(
            "Phase 9 Linux acceptance must not use the mutable host browser runtime"
        )
    immutable_pull = f"docker pull {PHASE_9_LINUX_PLAYWRIGHT_IMAGE}"
    if workflow.count(immutable_pull) != 1:
        raise AssertionError(
            "Phase 9 CI must pre-pull the exact immutable Linux browser image once"
        )
    phase5_postgres_tests = normalized(ROOT / "tests/test_phase5_postgres.py")
    if '"9": "0007_phase7"' not in phase5_postgres_tests:
        raise AssertionError("Phase 9 PostgreSQL acceptance does not preserve head 0007_phase7")


def verify_phase10_static() -> None:
    for relative_path in PHASE_10_REQUIRED_PATHS:
        if not (ROOT / relative_path).exists():
            raise AssertionError(f"Missing Phase 10 path: {relative_path}")

    if git_text("show", "-s", "--format=%T", PHASE_9_BASELINE_SHA) != EXPECTED_PHASE_9_TREE:
        raise AssertionError("The authorized Phase 9 baseline tree does not match")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE_9_BASELINE_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise AssertionError("Phase 10 HEAD is not descended from the accepted Phase 9 baseline")

    changed_paths = {
        path.replace("\\", "/")
        for path in git_text("diff", "--name-only", PHASE_9_BASELINE_SHA, "--").splitlines()
        if path
    }
    changed_paths.update(
        path.replace("\\", "/")
        for path in git_text("diff", "--cached", "--name-only", "--").splitlines()
        if path
    )
    changed_paths.update(
        path.replace("\\", "/")
        for path in git_text("ls-files", "--others", "--exclude-standard", "--").splitlines()
        if path
    )
    forbidden_changes = sorted(changed_paths - PHASE_10_ALLOWED_WRITES)
    if forbidden_changes:
        raise AssertionError(
            "Phase 10 changed paths outside the exact allowlist: " + ", ".join(forbidden_changes)
        )

    snapshot_root = ROOT / PHASE_10_VISUAL_SNAPSHOT_DIRECTORY
    actual_baselines = {path.name for path in snapshot_root.glob("*.png")}
    if actual_baselines != PHASE_10_VISUAL_BASELINES:
        missing = sorted(PHASE_10_VISUAL_BASELINES - actual_baselines)
        unexpected = sorted(actual_baselines - PHASE_10_VISUAL_BASELINES)
        raise AssertionError(
            f"Phase 10 visual baseline matrix is not exact; missing={missing}, "
            f"unexpected={unexpected}"
        )
    empty_baselines = sorted(
        path.name for path in snapshot_root.glob("*.png") if path.stat().st_size == 0
    )
    if empty_baselines:
        raise AssertionError(f"Phase 10 visual baselines are empty: {empty_baselines}")

    migration_root = ROOT / "services/api/migrations/versions"
    expected_migrations = set(PHASE_1_7_MIGRATION_SHA256) | {
        "services/api/migrations/versions/0008_phase10_local_paper.py"
    }
    migration_paths = {path.relative_to(ROOT).as_posix() for path in migration_root.glob("*.py")}
    if migration_paths != expected_migrations:
        raise AssertionError("Phase 10 requires exactly migrations 0001 through 0008")
    for path, expected_sha256 in PHASE_1_7_MIGRATION_SHA256.items():
        actual_sha256 = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise AssertionError(f"Phase 10 changed an accepted migration: {path}")
    migration = normalized(migration_root / "0008_phase10_local_paper.py")
    for evidence in (
        'revision: str = "0008_phase10"',
        'down_revision: str | None = "0007_phase7"',
        PHASE_10_APPEND_ONLY_ERROR,
        "CREATE FUNCTION reject_phase10_paper_mutation()",
        "CREATE TRIGGER {table}_immutable",
        "CREATE TRIGGER {table}_no_truncate",
        "paper_simulation_runs_25_authority_commit",
        "phase10_lock_authority_version()",
        "phase10-local-simulation-revalidation-v1",
        "DEFERRABLE INITIALLY DEFERRED",
    ):
        if evidence not in migration:
            raise AssertionError(f"Phase 10 migration is missing evidence: {evidence}")
    for table in PHASE_10_TABLES:
        if f'op.create_table(\n        "{table}"' not in migration:
            raise AssertionError(f"Phase 10 migration is missing table {table}")

    paper_root = ROOT / "services/paper/src/fable5_paper"
    forbidden_import_roots = FORBIDDEN_VENDOR_SDK_MODULES | {
        "aiohttp",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "urllib3",
    }
    for path in paper_root.rglob("*.py"):
        forbidden = imported_module_roots(path) & forbidden_import_roots
        if forbidden:
            raise AssertionError(
                f"Phase 10 local simulator imports a vendor/network module: {path} {forbidden}"
            )
    dependencies = normalized(ROOT / "pyproject.toml").casefold()
    for dependency in ("alpaca-py", "ib_insync", "ibapi", "ccxt"):
        if dependency in dependencies:
            raise AssertionError(f"Phase 10 added a prohibited execution dependency: {dependency}")

    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    expected_paths = {
        "/v1/local-simulations": {"get", "post"},
        "/v1/local-simulations/{simulation_run_id}": {"get"},
    }
    actual_paths: dict[str, set[str]] = {}
    for path, operations in openapi["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path in expected_paths or "paper-simulation" in tags:
            actual_paths[path] = set(operations) & {"get", "post", "put", "patch", "delete"}
    if actual_paths != expected_paths:
        raise AssertionError(f"Phase 10 API surface is not exact: {actual_paths}")
    components = openapi["components"]["schemas"]
    request_schema = components["PaperSimulationCreateRequest"]
    expected_request_fields = {"approval_assessment_id", "simulation_idempotency_key"}
    if (
        set(request_schema.get("properties", {})) != expected_request_fields
        or set(request_schema.get("required", [])) != expected_request_fields
        or request_schema.get("additionalProperties") is not False
    ):
        raise AssertionError("Phase 10 request accepts client-authoritative simulation values")
    artifact_properties = components["PaperSimulationArtifact"].get("properties", {})
    expected_constants = {
        "synthetic": True,
        "simulated_paper_only": True,
        "local_mock_only": True,
        "external_submission": False,
        "external_routing_absent": True,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
    for field, expected in expected_constants.items():
        if artifact_properties.get(field, {}).get("const") is not expected:
            raise AssertionError(f"Phase 10 safety flag is not a schema constant: {field}")
    if artifact_properties.get("transition_revalidation_proof", {}).get("$ref") != (
        "#/components/schemas/PaperTransitionRevalidationProof"
    ):
        raise AssertionError("Phase 10 schema omits its decision-time revalidation proof")

    contracts = normalized(ROOT / "services/paper/src/fable5_paper/contracts.py")
    workflow = normalized(ROOT / "services/paper/src/fable5_paper/workflow.py")
    for required in (
        "PAPER_CHECK_ORDER",
        "PaperTransitionRevalidationProof",
        "revalidation_proof_sha256",
        "phase10-a-local-mock-qa-v1",
        "external_submission: Literal[False]",
        "live_path_absent: Literal[True]",
        "no_personalized_investment_advice: Literal[True]",
        "no_real_performance_claimed: Literal[True]",
    ):
        if required not in contracts:
            raise AssertionError(f"Phase 10 contract invariant is missing: {required}")
    for required in (
        "ApprovalWorkflow(",
        "PaperSimulationOutcome.BLOCKED",
        "build_simulation_ledger",
        "build_transition_revalidation_proof",
        "phase10_code_version_git_sha_missing",
    ):
        if required not in workflow:
            raise AssertionError(f"Phase 10 fail-closed workflow evidence is missing: {required}")

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase10-contract.type-test.ts")
    frontend_api = normalized(ROOT / "services/frontend/src/lib/api.ts")
    for required in (
        "PaperSimulationArtifact:",
        "PaperSimulationCreateRequest:",
        "PaperSimulationSummary:",
        '"/v1/local-simulations"',
        '"/v1/local-simulations/{simulation_run_id}"',
    ):
        if required not in generated:
            raise AssertionError(f"Generated Phase 10 contract is missing {required}")
    for required in (
        "PaperSimulationCreateRequest",
        "@ts-expect-error",
        "simulation_idempotency_key",
    ):
        if required not in type_test:
            raise AssertionError(f"Phase 10 generated-contract type test is missing {required}")
    for required in ("createLocalSimulation", "listLocalSimulations", "getLocalSimulation"):
        if required not in frontend_api:
            raise AssertionError(f"Phase 10 typed frontend client is missing {required}")

    paper_workspace = normalized(ROOT / "services/frontend/src/app/paper/PaperStatusWorkspace.tsx")
    for required in (
        "SIMULATED",
        "LOCAL MOCK",
        "Run deterministic local simulation",
        "no personalized investment advice",
        "no live path",
    ):
        if required.casefold() not in paper_workspace.casefold():
            raise AssertionError(f"Phase 10 UI safety copy is missing: {required}")
    if any(
        field in paper_workspace
        for field in ('name="quantity"', 'name="price"', 'name="side"', 'name="symbol"')
    ):
        raise AssertionError("Phase 10 UI exposes a client-authoritative trade parameter")

    inherited_accessibility = normalized(
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts"
    )
    inherited_visual = normalized(ROOT / "services/frontend/e2e/phase8.visual.spec.ts")
    for spec_name, source in (
        ("phase8.accessibility.spec.ts", inherited_accessibility),
        ("phase8.visual.spec.ts", inherited_visual),
    ):
        if (
            'process.env.FABLE5_VERIFY_PHASE ?? "10"' not in source
            or "inheritedModes" not in source
            or 'mode.path !== "/paper"' not in source
        ):
            raise AssertionError(
                f"Phase 10 does not preserve active inherited browser coverage in {spec_name}"
            )

    pyproject = normalized(ROOT / "pyproject.toml")
    if pyproject.count('"services/paper/src"') < 3 or '"services/paper/tests"' not in pyproject:
        raise AssertionError("Phase 10 paper package is absent from build, test, or typing paths")
    for dockerfile in ("services/api/Dockerfile", "services/jobs/Dockerfile"):
        if "COPY services/paper ./services/paper" not in normalized(ROOT / dockerfile):
            raise AssertionError(f"Phase 10 paper package is absent from {dockerfile}")
    phase5_postgres_tests = normalized(ROOT / "tests/test_phase5_postgres.py")
    if '"10": "0008_phase10"' not in phase5_postgres_tests:
        raise AssertionError("Phase 10 PostgreSQL acceptance does not select head 0008_phase10")
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    immutable_pull = f"docker pull {PHASE_9_LINUX_PLAYWRIGHT_IMAGE}"
    if workflow.count(immutable_pull) != 1:
        raise AssertionError(
            "Phase 10 CI must pre-pull the exact immutable Linux browser image once"
        )
    if PHASE_10_LINUX_SNAPSHOT_FLAG in workflow or "FABLE5_UPDATE_SNAPSHOTS" in workflow:
        raise AssertionError("Phase 10 CI must compare, never regenerate, visual baselines")
    if "python scripts/verify_phase1.py --phase 10" not in workflow:
        raise AssertionError("Phase 10 CI does not run the full Compose verifier")
    readme = normalized(ROOT / "README.md")
    for required in (
        "## Phase 10 implementation status",
        "scripts\\verify_phase1.py --phase 10",
        "binds and reports the same commit SHA/tree",
        "fable5_acceptance_*",
    ):
        if required not in readme:
            raise AssertionError(f"Phase 10 README closure truth is missing: {required}")


def verify_static(phase: int = 1) -> None:
    if phase == 9:
        with phase9_stage(phase, "phase1_8_static"):
            verify_static_inherited(8)
        with phase9_stage(phase, "phase9_static"):
            verify_phase9_static()
        print("Static repository policy checks passed for Phase 9.")
        return
    if phase == 10:
        verify_static_inherited(10, announce=False)
        verify_phase10_static()
        print("Static repository policy checks passed for Phase 10.")
        return
    verify_static_inherited(phase)


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


def acceptance_environment(
    phase: int = 1,
    *,
    expected_git_identity: tuple[str, str] | None = None,
) -> tuple[dict[str, str], str, str]:
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
    generate_linux_snapshots = phase == 10 and environment.get(PHASE_10_LINUX_SNAPSHOT_FLAG) == "1"
    browser_api_url = (
        f"http://host.docker.internal:{api_port}" if generate_linux_snapshots else api_url
    )
    cors_origins = [f"http://localhost:{frontend_port}", frontend_url]
    if generate_linux_snapshots:
        cors_origins.append(f"http://host.docker.internal:{frontend_port}")
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
            "FABLE5_CORS_ORIGINS": json.dumps(cors_origins),
            "NEXT_PUBLIC_API_URL": browser_api_url,
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
        if phase == 10 and expected_git_identity is not None:
            git_tree = subprocess.run(
                ["git", "show", "-s", "--format=%T", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if (git_sha, git_tree) != expected_git_identity:
                raise AssertionError(
                    "Phase 10 source identity changed between clean preflight and "
                    "environment binding"
                )
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
    timeout_seconds: float = 10,
) -> dict[str, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        urllib.request.urlopen(request, timeout=timeout_seconds)
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


def phase6_request_timeout_profile(phase: int) -> tuple[int, int, int]:
    if phase == 9:
        return (
            PHASE_9_PHASE6_REQUEST_TIMEOUT_SECONDS,
            PHASE_9_PHASE6_DETAIL_TIMEOUT_SECONDS,
            PHASE_9_PHASE6_VALIDATION_TIMEOUT_SECONDS,
        )
    return (
        PHASE_6_REQUEST_TIMEOUT_SECONDS,
        PHASE_6_DETAIL_TIMEOUT_SECONDS,
        PHASE_6_VALIDATION_TIMEOUT_SECONDS,
    )


@contextmanager
def phase6_request_timeout_context(phase: int) -> Iterator[None]:
    token = PHASE_6_TIMEOUT_PHASE.set(phase)
    try:
        yield
    finally:
        PHASE_6_TIMEOUT_PHASE.reset(token)


def verify_phase6_api(api_url: str) -> dict[str, str]:
    (
        request_timeout_seconds,
        detail_timeout_seconds,
        validation_timeout_seconds,
    ) = phase6_request_timeout_profile(PHASE_6_TIMEOUT_PHASE.get())
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

    mapping_results = request_json(
        f"{api_url}/v1/mappings?limit=100",
        timeout_seconds=validation_timeout_seconds,
    )
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
                timeout_seconds=validation_timeout_seconds,
            )
            repeated = request_json(
                f"{api_url}/v1/data-snapshots",
                method="POST",
                payload=payload,
                timeout_seconds=validation_timeout_seconds,
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
            timeout_seconds=request_timeout_seconds,
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
            timeout_seconds=request_timeout_seconds,
        )
        repeated = request_json(
            f"{api_url}/v1/research-runs",
            method="POST",
            payload=payload_for(configuration_id),
            timeout_seconds=request_timeout_seconds,
        )
        if not isinstance(created, dict) or created != repeated:
            raise AssertionError(f"Phase 6 {configuration_id} run was not idempotent")
        artifacts[configuration_id] = created

    blocked = request_error_json(
        f"{api_url}/v1/research-runs",
        expected_status=422,
        payload=payload_for("phase6-c-fail-corroboration-v2"),
        timeout_seconds=validation_timeout_seconds,
    )
    repeated_blocked = request_error_json(
        f"{api_url}/v1/research-runs",
        expected_status=422,
        payload=payload_for("phase6-c-fail-corroboration-v2"),
        timeout_seconds=validation_timeout_seconds,
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
        timeout_seconds=validation_timeout_seconds,
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
        report = request_json(
            f"{api_url}/v1/evaluation-reports/{report_id}",
            timeout_seconds=validation_timeout_seconds,
        )
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
            f"/versions/{report['evaluation_policy_version']}",
            timeout_seconds=validation_timeout_seconds,
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
        # Complete Phase 6 artifacts intentionally include the full deterministic
        # sample/trial lineage.  Phase 8 exercises every one of these GET-by-id
        # responses, so allow the immutable byte-stability read to finish on
        # slower local container filesystems without changing the assertion.
        if (
            request_json(
                f"{api_url}/v1/research-runs/{run_id}",
                timeout_seconds=detail_timeout_seconds,
            )
            != artifact
        ):
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

    listing = request_json(
        f"{api_url}/v1/research-runs?limit=100",
        timeout_seconds=validation_timeout_seconds,
    )
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


def provision_phase7_evidence(
    project: str,
    environment: dict[str, str],
    phase6_run_ids: dict[str, str],
) -> dict[str, object]:
    serialized_run_ids = json.dumps(phase6_run_ids, sort_keys=True)
    script = f"""
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fable5_research.repository import ResearchRepository
from fable5_risk.contracts import ApprovalAssessmentCreateRequest
from fable5_risk.fixtures import (
    ApprovalEvidenceBundle,
    build_approval_risk_input,
    build_breach_evidence_bundle,
    build_expired_evidence_bundle,
    build_nominal_evidence_bundle,
    build_revocation_evidence_profile,
    build_stale_evidence_bundle,
    build_uncomputable_evidence_bundle,
    phase6_lineage_from_research_artifact,
)
from fable5_risk.repository import RiskRepository

run_ids = json.loads({serialized_run_ids!r})
assessment_time_utc = datetime.now(UTC)
research_repository = ResearchRepository(os.environ["FABLE5_DATABASE_URL"])
risk_repository = RiskRepository(os.environ["FABLE5_DATABASE_URL"])

def request_payload(lineage, bundle):
    request = ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=bundle.authorization.human_authorization_evidence_id,
        risk_input_id=bundle.risk_input.risk_input_id,
    )
    return request.model_dump(mode="json")

def provision(lineage, bundle):
    risk_repository.provision_evidence(
        bundle.policy,
        bundle.scope,
        bundle.authorization,
        bundle.risk_input,
    )
    return request_payload(lineage, bundle)

try:
    lineages = {{
        configuration_id: phase6_lineage_from_research_artifact(
            research_repository.get_run(UUID(run_id))
        )
        for configuration_id, run_id in run_ids.items()
    }}
    research_requests = {{
        configuration_id: provision(
            lineage,
            build_nominal_evidence_bundle(
                lineage,
                assessment_time_utc=assessment_time_utc,
            ),
        )
        for configuration_id, lineage in lineages.items()
    }}

    eligible = lineages["phase6-a-pass-v2"]
    scenario_builders = {{
        "expired": build_expired_evidence_bundle,
        "stale": build_stale_evidence_bundle,
        "uncomputable": build_uncomputable_evidence_bundle,
        "breach": build_breach_evidence_bundle,
    }}
    scenario_requests = {{
        name: provision(
            eligible,
            builder(eligible, assessment_time_utc=assessment_time_utc),
        )
        for name, builder in scenario_builders.items()
    }}

    base = build_nominal_evidence_bundle(
        eligible,
        assessment_time_utc=assessment_time_utc,
    )
    conflicting_lineage = lineages["phase6-a-fail-cost-v2"]
    conflicting_risk = build_approval_risk_input(
        conflicting_lineage,
        base.policy,
        base.scope,
        observed_at_utc=assessment_time_utc - timedelta(minutes=5),
    )
    conflicting = ApprovalEvidenceBundle(
        policy=base.policy,
        scope=base.scope,
        authorization=base.authorization,
        risk_input=conflicting_risk,
    )
    scenario_requests["conflicting"] = provision(eligible, conflicting)

    revocation_evidence = build_revocation_evidence_profile()
    print(json.dumps({{
        "research": research_requests,
        "scenarios": scenario_requests,
        "revocation_evidence_id": str(revocation_evidence.revocation_evidence_id),
    }}, sort_keys=True))
finally:
    risk_repository.dispose()
    research_repository.dispose()
"""
    try:
        result = compose_exec(
            project,
            environment,
            "api",
            ["python", "-c", script],
        )
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            f"Phase 7 evidence provisioning failed. stdout={exc.stdout!r} stderr={exc.stderr!r}"
        ) from exc
    try:
        provisioned = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Phase 7 evidence provisioning did not return JSON: {result.stdout!r}"
        ) from exc
    if not isinstance(provisioned, dict):
        raise AssertionError("Phase 7 evidence provisioning did not return an object")
    return provisioned


def verify_phase7_api(
    project: str,
    environment: dict[str, str],
    api_url: str,
    phase6_run_ids: dict[str, str],
) -> dict[str, str]:
    expected_run_ids = {
        "phase6-a-pass-v2",
        "phase6-a-fail-cost-v2",
        "phase6-b-pass-v2",
        "phase6-b-fail-crash-v2",
        "phase6-c-pass-v2",
    }
    if set(phase6_run_ids) != expected_run_ids:
        raise AssertionError(
            "Phase 7 requires exactly the five persisted Phase 6 corpus artifacts; "
            f"received {sorted(phase6_run_ids)}"
        )
    if "phase6-c-fail-corroboration-v2" in phase6_run_ids:
        raise AssertionError("Phase 7 received the blocked corroboration-negative Phase 6 request")

    provisioned = provision_phase7_evidence(project, environment, phase6_run_ids)
    research_requests = provisioned.get("research")
    scenario_requests = provisioned.get("scenarios")
    revocation_evidence_id = provisioned.get("revocation_evidence_id")
    if (
        not isinstance(research_requests, dict)
        or set(research_requests) != expected_run_ids
        or not isinstance(scenario_requests, dict)
        or set(scenario_requests) != {"expired", "stale", "conflicting", "uncomputable", "breach"}
        or not isinstance(revocation_evidence_id, str)
    ):
        raise AssertionError("Phase 7 independent evidence provisioning is incomplete")

    eligible_request = research_requests["phase6-a-pass-v2"]
    if not isinstance(eligible_request, dict):
        raise AssertionError("Phase 7 eligible request references are malformed")
    expected_request_fields = {
        "research_run_id",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "human_authorization_evidence_id",
        "risk_input_id",
    }
    if set(eligible_request) != expected_request_fields:
        raise AssertionError("Phase 7 assessment request is not reference-only")

    missing_evidence = request_error_json(
        f"{api_url}/v1/approval-assessments",
        expected_status=422,
        payload={"research_run_id": phase6_run_ids["phase6-a-pass-v2"]},
    )
    if not isinstance(missing_evidence.get("detail"), list):
        raise AssertionError("Phase 6 PASS_RESEARCH alone did not fail typed validation")
    client_authority = request_error_json(
        f"{api_url}/v1/approval-assessments",
        expected_status=422,
        payload={**eligible_request, "outcome": "APPROVED_PAPER"},
    )
    if not isinstance(client_authority.get("detail"), list):
        raise AssertionError("Phase 7 accepted a client-supplied approval outcome")
    unknown_request = {
        **eligible_request,
        "approval_policy_version_id": "00000000-0000-5000-8000-000000000707",
    }
    missing = request_error_json(
        f"{api_url}/v1/approval-assessments",
        expected_status=404,
        payload=unknown_request,
    )
    if "not found" not in str(missing.get("detail", "")).casefold():
        raise AssertionError("Phase 7 missing evidence did not fail closed")

    barrier = Barrier(2)

    def create_positive() -> dict[str, object] | list[object]:
        barrier.wait()
        return request_json(
            f"{api_url}/v1/approval-assessments",
            method="POST",
            payload=eligible_request,
            timeout_seconds=30,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent = tuple(executor.map(lambda _: create_positive(), range(2)))
    if not all(isinstance(item, dict) for item in concurrent) or concurrent[0] != concurrent[1]:
        raise AssertionError("Concurrent identical Phase 7 assessment creation was not idempotent")
    positive = dict(concurrent[0])

    checks = positive.get("checks")
    lineage = positive.get("phase6_lineage")
    if not isinstance(checks, list) or not isinstance(lineage, dict):
        raise AssertionError("Phase 7 positive artifact omitted checks or Phase 6 lineage")
    if (
        positive.get("outcome") != "APPROVED_PAPER"
        or positive.get("reason_codes") != ["all_approval_and_risk_checks_passed"]
        or [item.get("code") for item in checks if isinstance(item, dict)]
        != list(PHASE_7_CHECK_CODES)
        or len(checks) != len(PHASE_7_CHECK_CODES)
        or any(not isinstance(item, dict) or item.get("status") != "PASS" for item in checks)
        or positive.get("synthetic") is not True
        or positive.get("simulated_paper_only") is not True
        or positive.get("execution_authorized") is not False
        or positive.get("execution_ready") is not False
        or positive.get("no_personalized_investment_advice") is not True
        or positive.get("no_real_performance_claimed") is not True
        or positive.get("phase7_code_version_git_sha") != environment["FABLE5_CODE_VERSION_GIT_SHA"]
    ):
        raise AssertionError("Phase 7 positive artifact violated approval or safety invariants")
    if (
        lineage.get("research_run_id") != phase6_run_ids["phase6-a-pass-v2"]
        or lineage.get("research_configuration_id") != "phase6-a-pass-v2"
        or lineage.get("promotion_state") != "PASS_RESEARCH"
        or lineage.get("research_status") != "completed"
        or lineage.get("gate_codes")
        != [
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
        or not isinstance(lineage.get("snapshot_bindings"), list)
        or len(lineage["snapshot_bindings"]) != 7
    ):
        raise AssertionError("Phase 7 positive artifact lost exact Phase 6 A lineage")
    for hash_field in (
        "lineage_sha256",
        "research_artifact_sha256",
        "research_request_fingerprint_sha256",
        "research_configuration_sha256",
        "mapping_input_sha256",
        "specification_sha256",
        "research_pipeline_input_sha256",
        "feature_lineage_sha256",
        "snapshot_bundle_sha256",
        "source_reproduction_audit_sha256",
        "phase5_policy_sha256",
        "phase5_fixture_sha256",
        "evaluation_report_sha256",
        "phase5_trial_set_sha256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", str(lineage.get(hash_field))) is None:
            raise AssertionError(f"Phase 7 complete lineage omitted {hash_field}")

    assessment_id = positive.get("assessment_id")
    artifact_sha256 = positive.get("artifact_sha256")
    if (
        not isinstance(assessment_id, str)
        or not isinstance(artifact_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is None
        or request_json(f"{api_url}/v1/approval-assessments/{assessment_id}") != positive
    ):
        raise AssertionError("Phase 7 positive assessment create/read evidence is inconsistent")

    rejection_ids: set[str] = set()
    for configuration_id in sorted(expected_run_ids - {"phase6-a-pass-v2"}):
        payload = research_requests[configuration_id]
        if not isinstance(payload, dict):
            raise AssertionError(f"Phase 7 {configuration_id} references are malformed")
        rejected = request_json(
            f"{api_url}/v1/approval-assessments",
            method="POST",
            payload=payload,
            timeout_seconds=30,
        )
        if not isinstance(rejected, dict):
            raise AssertionError(f"Phase 7 {configuration_id} rejection is malformed")
        rejected_checks = rejected.get("checks")
        research_check = (
            next(
                (
                    item
                    for item in rejected_checks
                    if isinstance(item, dict) and item.get("code") == "RESEARCH_PASS"
                ),
                None,
            )
            if isinstance(rejected_checks, list)
            else None
        )
        if (
            rejected.get("outcome") != "FAIL_REJECT"
            or not isinstance(research_check, dict)
            or research_check.get("status") != "FAIL"
            or research_check.get("reason_code") != "phase6_research_not_eligible"
            or rejected.get("phase6_lineage", {}).get("research_configuration_id")
            != configuration_id
        ):
            raise AssertionError(
                f"Phase 7 derived eligibility from an id token for {configuration_id}"
            )
        rejected_id = rejected.get("assessment_id")
        if isinstance(rejected_id, str):
            rejection_ids.add(rejected_id)

    expected_scenario_checks = {
        "expired": ("AUTHORIZATION_CURRENT", "BLOCKED"),
        "stale": ("RISK_INPUT_FRESH", "BLOCKED"),
        "conflicting": ("SCOPE_MATCH", "FAIL"),
        "uncomputable": ("NOTIONAL_LIMIT", "UNCOMPUTABLE"),
        "breach": ("NOTIONAL_LIMIT", "FAIL"),
    }
    for scenario, (check_code, status_value) in expected_scenario_checks.items():
        payload = scenario_requests[scenario]
        if not isinstance(payload, dict):
            raise AssertionError(f"Phase 7 {scenario} references are malformed")
        rejected = request_json(
            f"{api_url}/v1/approval-assessments",
            method="POST",
            payload=payload,
            timeout_seconds=30,
        )
        if not isinstance(rejected, dict) or rejected.get("outcome") != "FAIL_REJECT":
            raise AssertionError(f"Phase 7 {scenario} evidence did not fail closed")
        rejected_checks = rejected.get("checks")
        target = (
            next(
                (
                    item
                    for item in rejected_checks
                    if isinstance(item, dict) and item.get("code") == check_code
                ),
                None,
            )
            if isinstance(rejected_checks, list)
            else None
        )
        if not isinstance(target, dict) or target.get("status") != status_value:
            raise AssertionError(f"Phase 7 {scenario} did not persist {check_code}={status_value}")
        rejected_id = rejected.get("assessment_id")
        if isinstance(rejected_id, str):
            rejection_ids.add(rejected_id)

    invalid_revocation = request_error_json(
        f"{api_url}/v1/approval-revocations",
        expected_status=422,
        payload={
            "human_authorization_evidence_id": eligible_request["human_authorization_evidence_id"],
            "revocation_evidence_id": revocation_evidence_id,
            "revoked": True,
        },
    )
    if not isinstance(invalid_revocation.get("detail"), list):
        raise AssertionError("Phase 7 accepted client-supplied revocation state")
    unknown_revocation = request_error_json(
        f"{api_url}/v1/approval-revocations",
        expected_status=404,
        payload={
            "human_authorization_evidence_id": eligible_request["human_authorization_evidence_id"],
            "revocation_evidence_id": "00000000-0000-5000-8000-000000000708",
        },
    )
    if "not found" not in str(unknown_revocation.get("detail", "")).casefold():
        raise AssertionError("Phase 7 accepted unknown revocation evidence")

    revocation_request = {
        "human_authorization_evidence_id": eligible_request["human_authorization_evidence_id"],
        "revocation_evidence_id": revocation_evidence_id,
    }
    revocation = request_json(
        f"{api_url}/v1/approval-revocations",
        method="POST",
        payload=revocation_request,
    )
    repeated_revocation = request_json(
        f"{api_url}/v1/approval-revocations",
        method="POST",
        payload=revocation_request,
    )
    if not isinstance(revocation, dict) or revocation != repeated_revocation:
        raise AssertionError("Phase 7 revocation creation was not idempotent")
    revocation_id = revocation.get("revocation_id")
    if (
        not isinstance(revocation_id, str)
        or revocation.get("synthetic") is not True
        or revocation.get("simulated_paper_only") is not True
        or revocation.get("execution_authorized") is not False
        or revocation.get("execution_ready") is not False
        or request_json(f"{api_url}/v1/approval-revocations/{revocation_id}") != revocation
    ):
        raise AssertionError("Phase 7 revocation artifact violated safety or read invariants")
    filtered_revocations = request_json(
        f"{api_url}/v1/approval-revocations?human_authorization_evidence_id="
        + str(eligible_request["human_authorization_evidence_id"])
        + "&limit=100"
    )
    if not isinstance(filtered_revocations, list) or revocation_id not in {
        item.get("revocation_id") for item in filtered_revocations if isinstance(item, dict)
    }:
        raise AssertionError("Phase 7 revocation list/filter evidence is incomplete")

    revoked = request_json(
        f"{api_url}/v1/approval-assessments",
        method="POST",
        payload=eligible_request,
        timeout_seconds=30,
    )
    if not isinstance(revoked, dict):
        raise AssertionError("Phase 7 revoked assessment is malformed")
    revoked_checks = revoked.get("checks")
    revocation_check = (
        next(
            (
                item
                for item in revoked_checks
                if isinstance(item, dict) and item.get("code") == "REVOCATION_CLEAR"
            ),
            None,
        )
        if isinstance(revoked_checks, list)
        else None
    )
    if (
        revoked.get("outcome") != "FAIL_REJECT"
        or revoked.get("assessment_id") == assessment_id
        or not isinstance(revocation_check, dict)
        or revocation_check.get("status") != "BLOCKED"
        or revocation_check.get("reason_code") != "authorization_revoked"
        or request_json(f"{api_url}/v1/approval-assessments/{assessment_id}") != positive
    ):
        raise AssertionError(
            "Phase 7 revocation did not block reuse while preserving historical approval bytes"
        )
    revoked_id = revoked.get("assessment_id")
    if isinstance(revoked_id, str):
        rejection_ids.add(revoked_id)

    assessments = request_json(f"{api_url}/v1/approval-assessments?limit=100")
    if not isinstance(assessments, list):
        raise AssertionError("Phase 7 assessment list is not an array")
    listed_ids = {item.get("assessment_id") for item in assessments if isinstance(item, dict)}
    if assessment_id not in listed_ids or not rejection_ids <= listed_ids:
        raise AssertionError("Phase 7 assessment list omitted positive or rejected evidence")

    print(
        "Phase 7 exact Phase 6 eligibility, complete lineage, reference-only requests, "
        "two-writer idempotency, expiry, staleness, conflict, uncomputable and breached "
        "risk, revocation, historical-byte preservation, and non-execution proof passed "
        f"(assessment_id={assessment_id}, artifact_sha256={artifact_sha256}, "
        f"revocation_id={revocation_id}, rejected_assessments={len(rejection_ids)})."
    )
    return {
        "positive_assessment_id": assessment_id,
        "positive_artifact_sha256": artifact_sha256,
        "revocation_id": revocation_id,
    }


def provision_phase10_source_assessment(
    project: str,
    environment: dict[str, str],
    api_url: str,
    phase6_run_ids: dict[str, str],
) -> dict[str, object]:
    eligible_run_id = phase6_run_ids.get("phase6-a-pass-v2")
    if not isinstance(eligible_run_id, str):
        raise AssertionError("Phase 10 requires the exact eligible Phase 6 A research run")
    script = f"""
import json
import os
from datetime import UTC, datetime
from uuid import UUID

from fable5_research.repository import ResearchRepository
from fable5_risk.contracts import ApprovalAssessmentCreateRequest
from fable5_risk.fixtures import (
    build_nominal_evidence_bundle,
    phase6_lineage_from_research_artifact,
)
from fable5_risk.repository import RiskRepository

research_repository = ResearchRepository(os.environ["FABLE5_DATABASE_URL"])
risk_repository = RiskRepository(os.environ["FABLE5_DATABASE_URL"])
try:
    artifact = research_repository.get_run(UUID({eligible_run_id!r}))
    lineage = phase6_lineage_from_research_artifact(artifact)
    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=datetime.now(UTC),
        policy_id="phase10-synthetic-approval-risk-policy",
        scope_id=f"phase10-synthetic-scope:{{lineage.research_run_id}}",
    )
    risk_repository.provision_evidence(
        bundle.policy,
        bundle.scope,
        bundle.authorization,
        bundle.risk_input,
    )
    request = ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=bundle.authorization.human_authorization_evidence_id,
        risk_input_id=bundle.risk_input.risk_input_id,
    )
    print(json.dumps(request.model_dump(mode="json"), sort_keys=True))
finally:
    risk_repository.dispose()
    research_repository.dispose()
"""
    result = compose_exec(project, environment, "api", ["python", "-c", script])
    try:
        request_payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise AssertionError("Phase 10 source provisioning did not return reference JSON") from exc
    if not isinstance(request_payload, dict) or set(request_payload) != {
        "research_run_id",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "human_authorization_evidence_id",
        "risk_input_id",
    }:
        raise AssertionError("Phase 10 source assessment request is not reference-only")
    source = request_json(
        f"{api_url}/v1/approval-assessments",
        method="POST",
        payload=request_payload,
        timeout_seconds=30,
    )
    if (
        not isinstance(source, dict)
        or source.get("outcome") != "APPROVED_PAPER"
        or source.get("research_run_id") != eligible_run_id
        or source.get("synthetic") is not True
        or source.get("execution_authorized") is not False
        or source.get("execution_ready") is not False
        or not isinstance(source.get("assessment_id"), str)
    ):
        raise AssertionError("Phase 10 fresh source assessment did not pass exact Phase 7 gates")
    return source


def verify_phase10_artifact(
    artifact: dict[str, object],
    *,
    environment: dict[str, str],
    expected_source_assessment_id: str,
    expected_outcome: str,
) -> None:
    checks = artifact.get("checks")
    ledger_entries = artifact.get("ledger_entries")
    configuration = artifact.get("configuration")
    revalidation_proof = artifact.get("transition_revalidation_proof")
    if (
        not isinstance(checks, list)
        or [item.get("code") for item in checks if isinstance(item, dict)]
        != list(PHASE_10_CHECK_CODES)
        or len(checks) != len(PHASE_10_CHECK_CODES)
        or not isinstance(ledger_entries, list)
        or not isinstance(configuration, dict)
        or not isinstance(revalidation_proof, dict)
    ):
        raise AssertionError(
            "Phase 10 artifact omitted its exact checks, revalidation, configuration, or ledger"
        )
    safety = {
        "synthetic": True,
        "simulated_paper_only": True,
        "local_mock_only": True,
        "external_submission": False,
        "external_routing_absent": True,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
    if (
        artifact.get("outcome") != expected_outcome
        or artifact.get("source_assessment_id") != expected_source_assessment_id
        or artifact.get("phase10_code_version_git_sha")
        != environment["FABLE5_CODE_VERSION_GIT_SHA"]
        or any(artifact.get(field) is not expected for field, expected in safety.items())
        or artifact.get("artifact_schema_version") != "phase10-local-paper-simulation-v1"
        or configuration.get("configuration_id") != "phase10-a-local-mock-qa-v1"
        or configuration.get("canonical_family") != "A_CROSS_SECTIONAL_EQUITY_RANKING"
        or configuration.get("model_id") != "sector-relative-rank-linear-v1"
        or configuration.get("signal_rule_id") != "phase6-a-score-positive-long-flat-v1"
        or configuration.get("mock_entity_id") != "SYNTHETIC-ASSET-001"
        or configuration.get("external_routing_absent") is not True
        or configuration.get("live_path_absent") is not True
        or configuration.get("llm_decision_role_absent") is not True
    ):
        raise AssertionError("Phase 10 artifact violated its exact local mock-only boundary")
    proof_sha256 = revalidation_proof.get("revalidation_proof_sha256")
    try:
        proof_id = uuid.UUID(str(revalidation_proof.get("revalidation_proof_id")))
    except ValueError as exc:
        raise AssertionError("Phase 10 revalidation proof ID is malformed") from exc
    if (
        revalidation_proof.get("schema_version") != "phase10-local-simulation-revalidation-v1"
        or proof_id.version != 5
        or re.fullmatch(r"[0-9a-f]{64}", str(proof_sha256)) is None
        or revalidation_proof.get("simulation_idempotency_key")
        != artifact.get("simulation_idempotency_key")
        or revalidation_proof.get("source_assessment_id") != artifact.get("source_assessment_id")
        or revalidation_proof.get("source_assessment_artifact_sha256")
        != artifact.get("source_assessment_artifact_sha256")
        or revalidation_proof.get("transition_assessment_id")
        != artifact.get("transition_assessment_id")
        or revalidation_proof.get("transition_assessment_artifact_sha256")
        != artifact.get("transition_assessment_artifact_sha256")
        or revalidation_proof.get("transition_currentness_state_sha256")
        != artifact.get("transition_currentness_state_sha256")
        or revalidation_proof.get("transition_revocation_set_sha256")
        != artifact.get("transition_revocation_set_sha256")
        or revalidation_proof.get("decision_time_utc") != artifact.get("decision_time_utc")
        or revalidation_proof.get("phase10_code_version_git_sha")
        != artifact.get("phase10_code_version_git_sha")
        or not isinstance(checks[1], dict)
        or proof_sha256 not in checks[1].get("evidence_sha256s", [])
    ):
        raise AssertionError(
            "Phase 10 revalidation proof is not bound through the fresh-transition check"
        )
    for hash_field in (
        "artifact_sha256",
        "request_fingerprint_sha256",
        "currentness_state_sha256",
        "source_assessment_artifact_sha256",
        "transition_assessment_artifact_sha256",
        "transition_currentness_state_sha256",
        "transition_revocation_set_sha256",
        "research_artifact_sha256",
        "phase6_lineage_sha256",
        "approval_policy_sha256",
        "approval_scope_sha256",
        "authorization_sha256",
        "risk_input_sha256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", str(artifact.get(hash_field))) is None:
            raise AssertionError(f"Phase 10 artifact omitted hash-bound evidence: {hash_field}")

    statuses = [item.get("status") for item in checks if isinstance(item, dict)]
    if expected_outcome == "SIMULATED_COMPLETE":
        if statuses != ["PASS"] * len(PHASE_10_CHECK_CODES) or len(ledger_entries) != 1:
            raise AssertionError("Completed Phase 10 artifact lacks all-pass checks or one ledger")
        ledger = ledger_entries[0]
        if not isinstance(ledger, dict):
            raise AssertionError("Phase 10 ledger is malformed")
        expected_ledger = {
            "entity_id": "SYNTHETIC-ASSET-001",
            "signal_state": "LONG",
            "simulated_side": "BUY",
            "fill_status": "SIMULATED_FILLED",
        }
        for field, expected in expected_ledger.items():
            if ledger.get(field) != expected:
                raise AssertionError(
                    f"Phase 10 deterministic ledger mismatch for {field}: {ledger.get(field)!r}"
                )
        expected_decimals = {
            "approved_proposed_notional": Decimal("50000"),
            "requested_quantity": Decimal("500"),
            "filled_quantity": Decimal("500"),
            "unfilled_quantity": Decimal("0"),
            "reference_price": Decimal("100"),
            "simulated_fill_price": Decimal("100.04"),
            "commission_cost": Decimal("5"),
            "spread_cost": Decimal("10"),
            "impact_cost": Decimal("5"),
            "latency_cost": Decimal("5"),
            "total_cost": Decimal("25"),
            "position_quantity_after": Decimal("500"),
            "cash_after": Decimal("949975"),
        }
        for field, expected in expected_decimals.items():
            try:
                actual = Decimal(str(ledger.get(field)))
            except Exception as exc:
                raise AssertionError(f"Phase 10 ledger decimal is malformed: {field}") from exc
            if actual != expected:
                raise AssertionError(
                    f"Phase 10 deterministic ledger mismatch for {field}: {actual!r}"
                )
        if (
            ledger.get("external_submission") is not False
            or ledger.get("live_path_absent") is not True
            or ledger.get("local_mock_only") is not True
        ):
            raise AssertionError("Phase 10 ledger lost its local non-execution literals")
    elif not any(status != "PASS" for status in statuses) or ledger_entries:
        raise AssertionError("Blocked Phase 10 artifact must have a non-pass check and no ledger")


def verify_phase10_api(
    project: str,
    environment: dict[str, str],
    api_url: str,
    phase6_run_ids: dict[str, str],
    revoked_source_assessment_id: str,
) -> dict[str, str]:
    source = provision_phase10_source_assessment(
        project,
        environment,
        api_url,
        phase6_run_ids,
    )
    source_assessment_id = str(source["assessment_id"])
    strict = request_error_json(
        f"{api_url}/v1/local-simulations",
        expected_status=422,
        payload={
            "approval_assessment_id": source_assessment_id,
            "simulation_idempotency_key": "phase10-complete-idempotency-key",
            "symbol": "CLIENT-AUTHORITY-FORBIDDEN",
        },
    )
    if not isinstance(strict.get("detail"), list):
        raise AssertionError("Phase 10 accepted a client-authoritative simulation field")
    missing = request_error_json(
        f"{api_url}/v1/local-simulations",
        expected_status=404,
        payload={
            "approval_assessment_id": "00000000-0000-4000-8000-000000000010",
            "simulation_idempotency_key": "phase10-missing-source-key",
        },
    )
    if "not found" not in str(missing.get("detail", "")).casefold():
        raise AssertionError("Phase 10 unknown assessment did not fail closed")

    complete_request = {
        "approval_assessment_id": source_assessment_id,
        "simulation_idempotency_key": "phase10-complete-idempotency-key",
    }
    barrier = Barrier(2)

    def create_complete() -> dict[str, object] | list[object]:
        barrier.wait()
        return request_json(
            f"{api_url}/v1/local-simulations",
            method="POST",
            payload=complete_request,
            timeout_seconds=30,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent = tuple(executor.map(lambda _: create_complete(), range(2)))
    if not all(isinstance(item, dict) for item in concurrent) or concurrent[0] != concurrent[1]:
        raise AssertionError("Concurrent identical Phase 10 creation was not byte-idempotent")
    complete = dict(concurrent[0])
    verify_phase10_artifact(
        complete,
        environment=environment,
        expected_source_assessment_id=source_assessment_id,
        expected_outcome="SIMULATED_COMPLETE",
    )
    simulation_run_id = complete.get("simulation_run_id")
    if (
        not isinstance(simulation_run_id, str)
        or request_json(f"{api_url}/v1/local-simulations/{simulation_run_id}") != complete
    ):
        raise AssertionError("Phase 10 completed create/read evidence is inconsistent")

    blocked_request = {
        "approval_assessment_id": revoked_source_assessment_id,
        "simulation_idempotency_key": "phase10-revoked-source-key",
    }
    blocked = request_json(
        f"{api_url}/v1/local-simulations",
        method="POST",
        payload=blocked_request,
        timeout_seconds=30,
    )
    repeated_blocked = request_json(
        f"{api_url}/v1/local-simulations",
        method="POST",
        payload=blocked_request,
        timeout_seconds=30,
    )
    if not isinstance(blocked, dict) or blocked != repeated_blocked:
        raise AssertionError("Phase 10 blocked transport retry was not idempotent")
    verify_phase10_artifact(
        blocked,
        environment=environment,
        expected_source_assessment_id=revoked_source_assessment_id,
        expected_outcome="BLOCKED",
    )
    transition_check = next(
        (
            item
            for item in blocked["checks"]
            if isinstance(item, dict) and item.get("code") == "TRANSITION_APPROVAL_FRESH"
        ),
        None,
    )
    if (
        not isinstance(transition_check, dict)
        or transition_check.get("status") != "BLOCKED"
        or transition_check.get("reason_code") != "transition_approval_not_fresh"
    ):
        raise AssertionError("Phase 10 did not visibly block fresh transition governance")

    listed = request_json(f"{api_url}/v1/local-simulations?limit=100")
    filtered = request_json(
        f"{api_url}/v1/local-simulations?approval_assessment_id={source_assessment_id}&limit=100"
    )
    listed_ids = {
        item.get("simulation_run_id")
        for item in listed
        if isinstance(listed, list) and isinstance(item, dict)
    }
    if (
        not isinstance(listed, list)
        or not isinstance(filtered, list)
        or simulation_run_id not in listed_ids
        or len(filtered) != 1
        or not isinstance(filtered[0], dict)
        or filtered[0].get("simulation_run_id") != simulation_run_id
    ):
        raise AssertionError("Phase 10 list/filter evidence omitted a terminal artifact")
    print(
        "Phase 10 reference-only completed/blocked APIs, exact fresh governance, concurrent "
        "idempotency, deterministic ledger reconciliation, create/read/list, strict client "
        "authority rejection, and local non-execution proof passed."
    )
    return {
        "completed_simulation_run_id": simulation_run_id,
        "blocked_simulation_run_id": str(blocked["simulation_run_id"]),
    }


def verify_phase8_evidence_timeline_api(api_url: str) -> None:
    summaries = request_json(f"{api_url}/v1/approval-assessments?limit=100")
    if not isinstance(summaries, list) or not summaries:
        raise AssertionError("Phase 8 timeline verification requires persisted assessments")

    resolved = 0
    conflicted = 0
    first_assessment_id: str | None = None
    for summary in summaries:
        if not isinstance(summary, dict) or not isinstance(summary.get("assessment_id"), str):
            raise AssertionError("Phase 8 assessment summary identity is malformed")
        assessment_id = summary["assessment_id"]
        if first_assessment_id is None:
            first_assessment_id = assessment_id
        assessment = request_json(f"{api_url}/v1/approval-assessments/{assessment_id}")
        try:
            timeline = request_json(
                f"{api_url}/v1/approval-assessments/{assessment_id}/evidence-timeline"
            )
        except urllib.error.HTTPError as exc:
            if exc.code != 409:
                raise
            try:
                conflict = json.loads(exc.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as parse_exc:
                raise AssertionError(
                    "Phase 8 conflicting timeline did not return deterministic JSON"
                ) from parse_exc
            if conflict != {
                "detail": "Immutable Phase 7 approval evidence conflicts with persisted lineage."
            }:
                raise AssertionError(
                    "Phase 8 conflicting timeline did not use the existing "
                    "fail-closed 409 semantics"
                ) from exc
            conflicted += 1
            continue
        if not isinstance(assessment, dict) or not isinstance(timeline, dict):
            raise AssertionError("Phase 8 complete assessment or timeline artifact is malformed")
        if set(timeline) != {
            "assessment_id",
            "assessment_created_at_utc",
            "policy",
            "scope",
            "authorization",
            "risk_input",
        }:
            raise AssertionError(
                "Phase 8 timeline exposed evidence beyond identifiers, hashes, times"
            )
        if timeline.get("assessment_id") != assessment_id or timeline.get(
            "assessment_created_at_utc"
        ) != assessment.get("created_at_utc"):
            raise AssertionError("Phase 8 timeline lost its exact immutable assessment reference")

        expected_evidence = {
            "policy": (
                "approval_policy_version_id",
                "approval_policy_sha256",
                "policy_sha256",
                {"valid_from_utc", "expires_at_utc"},
            ),
            "scope": (
                "approval_scope_version_id",
                "approval_scope_sha256",
                "scope_sha256",
                {"valid_from_utc", "expires_at_utc"},
            ),
            "authorization": (
                "human_authorization_evidence_id",
                "authorization_sha256",
                "authorization_sha256",
                {"authorized_at_utc", "review_at_utc", "expires_at_utc"},
            ),
            "risk_input": (
                "risk_input_id",
                "risk_input_sha256",
                "risk_input_sha256",
                {"observed_at_utc"},
            ),
        }
        for evidence_name, (
            id_field,
            assessment_hash_field,
            timeline_hash_field,
            timestamp_fields,
        ) in expected_evidence.items():
            evidence = timeline.get(evidence_name)
            if not isinstance(evidence, dict):
                raise AssertionError(f"Phase 8 timeline omitted {evidence_name} evidence")
            expected_fields = {id_field, timeline_hash_field, *timestamp_fields}
            if set(evidence) != expected_fields:
                raise AssertionError(
                    f"Phase 8 {evidence_name} timeline fields are not exact: {sorted(evidence)}"
                )
            if (
                evidence.get(id_field) != assessment.get(id_field)
                or evidence.get(timeline_hash_field) != assessment.get(assessment_hash_field)
                or re.fullmatch(r"[0-9a-f]{64}", str(evidence.get(timeline_hash_field))) is None
                or any(
                    not isinstance(evidence.get(field), str) or not evidence[field]
                    for field in timestamp_fields
                )
            ):
                raise AssertionError(
                    f"Phase 8 {evidence_name} timeline did not revalidate exact references"
                )
        resolved += 1

    missing = request_error_json(
        f"{api_url}/v1/approval-assessments/00000000-0000-5000-8000-000000000808/evidence-timeline",
        expected_status=404,
        method="GET",
    )
    if missing != {"detail": "The requested immutable Phase 7 approval evidence was not found."}:
        raise AssertionError("Phase 8 missing timeline evidence did not fail closed")
    if first_assessment_id is None or resolved == 0:
        raise AssertionError("Phase 8 did not resolve an assessment timeline identity")
    if conflicted == 0:
        raise AssertionError(
            "Phase 8 acceptance corpus did not prove a conflicting timeline fails closed"
        )
    request_error_json(
        f"{api_url}/v1/approval-assessments/{first_assessment_id}/evidence-timeline",
        expected_status=405,
        method="POST",
        payload={},
    )
    print(
        "Phase 8 GET-only evidence timeline resolved and hash-revalidated "
        f"{resolved} immutable assessment artifacts; {conflicted} conflicting artifacts and "
        "unknown evidence failed closed."
    )


def phase9_linux_playwright_container_name(project: str) -> str:
    return f"{project}{PHASE_9_LINUX_PLAYWRIGHT_CONTAINER_SUFFIX}"


def phase9_linux_playwright_command(project: str, frontend_url: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        phase9_linux_playwright_container_name(project),
        "--label",
        f"com.docker.compose.project={project}",
        "--network",
        "host",
        "--ipc",
        "host",
        "--mount",
        f"type=bind,source={ROOT.resolve()},target=/work,readonly",
        "--workdir",
        "/work/services/frontend",
        "--env",
        f"PLAYWRIGHT_BASE_URL={frontend_url}",
        "--env",
        f"{PHASE_9_BROWSER_TIMEOUT_FLAG}=1",
        "--env",
        "CI=true",
        PHASE_9_LINUX_PLAYWRIGHT_IMAGE,
        "node",
        "../../node_modules/@playwright/test/cli.js",
        "test",
        "--reporter=json",
        "--output=/tmp/playwright-results",
    ]


def phase9_playwright_failure_records(report: object) -> list[dict[str, object]]:
    if not isinstance(report, dict):
        raise AssertionError("Phase 9 Playwright JSON report is not an object")
    stats = report.get("stats")
    suites = report.get("suites")
    if not isinstance(stats, dict) or not isinstance(suites, list):
        raise AssertionError("Phase 9 Playwright JSON report is incomplete")
    unexpected = stats.get("unexpected")
    if isinstance(unexpected, bool) or not isinstance(unexpected, int) or unexpected < 0:
        raise AssertionError("Phase 9 Playwright unexpected-result count is invalid")

    records: list[dict[str, object]] = []

    def visit_suite(suite: object) -> None:
        if not isinstance(suite, dict):
            raise AssertionError("Phase 9 Playwright suite is not an object")
        child_suites = suite.get("suites", [])
        specs = suite.get("specs", [])
        if not isinstance(child_suites, list) or not isinstance(specs, list):
            raise AssertionError("Phase 9 Playwright suite structure is invalid")
        for child in child_suites:
            visit_suite(child)
        for spec in specs:
            if not isinstance(spec, dict):
                raise AssertionError("Phase 9 Playwright spec is not an object")
            file_name = spec.get("file")
            line = spec.get("line")
            tests = spec.get("tests")
            if not isinstance(tests, list):
                raise AssertionError("Phase 9 Playwright spec tests are invalid")
            for test in tests:
                if not isinstance(test, dict):
                    raise AssertionError("Phase 9 Playwright test result is not an object")
                if test.get("status") != "unexpected":
                    continue
                if (
                    not isinstance(file_name, str)
                    or file_name not in PHASE_9_PLAYWRIGHT_FAILURE_LOCATIONS
                    or isinstance(line, bool)
                    or not isinstance(line, int)
                    or line not in PHASE_9_PLAYWRIGHT_FAILURE_LOCATIONS[file_name]
                ):
                    raise AssertionError("Phase 9 Playwright failure location is not allowlisted")
                project_name = test.get("projectName")
                timeout = test.get("timeout")
                results = test.get("results")
                expected_timeout = PHASE_9_PLAYWRIGHT_TIMEOUTS.get((file_name, line), 240_000)
                if project_name not in {"mobile", "tablet", "desktop"}:
                    raise AssertionError("Phase 9 Playwright failure project is not allowlisted")
                if (
                    isinstance(timeout, bool)
                    or not isinstance(timeout, int)
                    or timeout != expected_timeout
                    or not isinstance(results, list)
                    or not results
                ):
                    raise AssertionError("Phase 9 Playwright failure timing is invalid")
                result = results[-1]
                if not isinstance(result, dict):
                    raise AssertionError("Phase 9 Playwright final result is not an object")
                status = result.get("status")
                duration = result.get("duration")
                if status not in {"failed", "timedOut", "interrupted"}:
                    raise AssertionError("Phase 9 Playwright failure status is not allowlisted")
                if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
                    raise AssertionError("Phase 9 Playwright failure duration is invalid")
                records.append(
                    {
                        "duration_ms": duration,
                        "file": Path(file_name).name,
                        "line": line,
                        "project": project_name,
                        "status": status,
                        "timeout_ms": timeout,
                    }
                )

    for suite in suites:
        visit_suite(suite)
    if len(records) != unexpected:
        raise AssertionError("Phase 9 Playwright failure count does not match its JSON report")
    return sorted(
        records,
        key=lambda record: (
            str(record["file"]),
            int(record["line"]),
            str(record["project"]),
            str(record["status"]),
        ),
    )


def run_phase9_linux_playwright(
    command: list[str],
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    try:
        report = json.loads(completed.stdout)
        failures = phase9_playwright_failure_records(report)
    except (json.JSONDecodeError, AssertionError) as exc:
        raise RuntimeError(
            "Phase 9 Playwright did not produce a valid sanitized JSON report"
        ) from exc
    for failure in failures:
        print(
            PHASE_9_PLAYWRIGHT_RESULT_PREFIX
            + json.dumps(failure, sort_keys=True, separators=(",", ":"))
        )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)
    return completed


def cleanup_phase9_linux_playwright_container(
    project: str,
    environment: dict[str, str],
) -> None:
    subprocess.run(
        [
            "docker",
            "container",
            "rm",
            "--force",
            phase9_linux_playwright_container_name(project),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        env=environment,
    )


def verify_phase8_browser(
    project: str,
    environment: dict[str, str],
    frontend_url: str,
) -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm is required for Phase 8 browser verification")

    all_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
        *PHASE_5_TABLES,
        *PHASE_6_TABLES,
        *PHASE_7_TABLES,
    )
    phase = int(environment.get("FABLE5_VERIFY_PHASE", "8"))
    with phase9_stage(phase, "phase8_browser_pre_snapshot"):
        before = snapshot_tables(project, environment, all_tables)
    browser_environment = environment.copy()
    phase10_linux_profile = (
        phase == 10 and browser_environment.get(PHASE_10_LINUX_SNAPSHOT_FLAG) == "1"
    )
    browser_frontend_url = (
        frontend_url.replace("127.0.0.1", "host.docker.internal")
        if phase10_linux_profile and not sys.platform.startswith("linux")
        else frontend_url
    )
    browser_environment["PLAYWRIGHT_BASE_URL"] = browser_frontend_url
    browser_environment.pop(PHASE_9_BROWSER_TIMEOUT_FLAG, None)
    if phase == 9:
        browser_environment[PHASE_9_BROWSER_TIMEOUT_FLAG] = "1"
    linux_phase9 = phase == 9 and sys.platform.startswith("linux")
    linux_phase10 = phase == 10 and (sys.platform.startswith("linux") or phase10_linux_profile)
    if linux_phase9:
        command = phase9_linux_playwright_command(project, frontend_url)
    elif linux_phase10:
        command = phase10_linux_playwright_command(
            project,
            browser_frontend_url,
            spec_paths=PHASE_8_BROWSER_SPECS,
            output_path="/tmp/phase10-inherited-playwright-results",
        )
    elif phase == 10:
        command = [
            npm,
            "--workspace",
            "@fable5/frontend",
            "run",
            "test:e2e",
            "--",
            *PHASE_8_BROWSER_SPECS,
        ]
    else:
        command = [npm, "--workspace", "@fable5/frontend", "run", "test:e2e"]
    with phase9_stage(phase, "phase8_browser_playwright"):
        try:
            if linux_phase9:
                run_phase9_linux_playwright(command, browser_environment)
            else:
                run(command, env=browser_environment)
        finally:
            if linux_phase9:
                cleanup_phase9_linux_playwright_container(project, browser_environment)
            elif linux_phase10:
                cleanup_phase10_linux_playwright_container(project, browser_environment)
    with phase9_stage(phase, "phase8_browser_post_snapshot"):
        assert_snapshots_equal(
            before,
            snapshot_tables(project, environment, all_tables),
            "during Phase 8 GET-only browser QA",
        )
    coverage = "unaffected inherited modes and shared layout" if phase == 10 else "all four modes"
    print(
        f"Phase 8 browser QA passed {coverage}: accessibility, keyboard, reduced-motion, "
        "responsive, visual-regression, and at-most-two-interaction lineage checks without "
        "changing any Phase 1-7 table."
    )


def phase10_linux_playwright_container_name(project: str) -> str:
    return f"{project}_phase10_playwright"


def cleanup_phase10_linux_playwright_container(
    project: str,
    environment: dict[str, str],
) -> None:
    subprocess.run(
        [
            "docker",
            "container",
            "rm",
            "--force",
            phase10_linux_playwright_container_name(project),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        env=environment,
    )


def phase10_linux_playwright_command(
    project: str,
    frontend_url: str,
    *,
    generate_snapshots: bool = False,
    spec_paths: tuple[str, ...] = (
        "e2e/phase10.accessibility.spec.ts",
        "e2e/phase10.visual.spec.ts",
    ),
    output_path: str = "/tmp/phase10-playwright-results",
) -> list[str]:
    command = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        phase10_linux_playwright_container_name(project),
        "--label",
        f"com.docker.compose.project={project}",
    ]
    if sys.platform.startswith("linux"):
        command.extend(["--network", "host"])
    else:
        command.extend(["--add-host", "host.docker.internal:host-gateway"])
    mount = f"type=bind,source={ROOT},target=/work"
    if not generate_snapshots:
        mount += ",readonly"
    command.extend(
        [
            "--ipc",
            "host",
            "--mount",
            mount,
            "--workdir",
            "/work/services/frontend",
            "--env",
            f"PLAYWRIGHT_BASE_URL={frontend_url}",
            "--env",
            "CI=true",
            "--env",
            "FABLE5_VERIFY_PHASE=10",
        ]
    )
    if generate_snapshots:
        command.extend(
            [
                "--env",
                "FABLE5_UPDATE_SNAPSHOTS=1",
                "--env",
                "FABLE5_VISUAL_CORPUS=synthetic",
            ]
        )
    command.extend(
        [
            PHASE_9_LINUX_PLAYWRIGHT_IMAGE,
            "node",
            "../../node_modules/@playwright/test/cli.js",
            "test",
            *spec_paths,
            "--reporter=list",
            f"--output={output_path}",
        ]
    )
    return command


def verify_phase10_browser(
    project: str,
    environment: dict[str, str],
    frontend_url: str,
) -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm is required for Phase 10 browser verification")
    all_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
        *PHASE_5_TABLES,
        *PHASE_6_TABLES,
        *PHASE_7_TABLES,
        *PHASE_10_TABLES,
    )
    before = snapshot_tables(project, environment, all_tables)
    browser_environment = environment.copy()
    generate_linux_snapshots = browser_environment.get(PHASE_10_LINUX_SNAPSHOT_FLAG) == "1"
    if generate_linux_snapshots and (
        browser_environment.get("FABLE5_UPDATE_SNAPSHOTS") != "1"
        or browser_environment.get("FABLE5_VISUAL_CORPUS") != "synthetic"
    ):
        raise RuntimeError(
            "Phase 10 Linux snapshot generation requires both explicit synthetic update guards"
        )
    linux = sys.platform.startswith("linux") or generate_linux_snapshots
    browser_frontend_url = (
        frontend_url.replace("127.0.0.1", "host.docker.internal")
        if generate_linux_snapshots and not sys.platform.startswith("linux")
        else frontend_url
    )
    browser_environment["PLAYWRIGHT_BASE_URL"] = browser_frontend_url
    command = (
        phase10_linux_playwright_command(
            project,
            browser_frontend_url,
            generate_snapshots=generate_linux_snapshots,
        )
        if linux
        else [
            npm,
            "--workspace",
            "@fable5/frontend",
            "run",
            "test:e2e",
            "--",
            "e2e/phase10.accessibility.spec.ts",
            "e2e/phase10.visual.spec.ts",
        ]
    )
    try:
        run(command, env=browser_environment)
    finally:
        if linux:
            cleanup_phase10_linux_playwright_container(project, browser_environment)
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, all_tables),
        "during Phase 10 route-isolated browser QA",
    )
    print(
        "Phase 10 targeted browser QA passed accessibility, keyboard, responsive, completed/"
        "blocked visual regression, and zero-database-write proof."
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


def verify_phase7_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    test_environment["FABLE5_CODE_VERSION_GIT_SHA"] = environment["FABLE5_CODE_VERSION_GIT_SHA"]
    test_environment["FABLE5_VERIFY_PHASE"] = "7"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "services/risk/tests/test_phase7_postgres.py", "-q"],
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
        raise AssertionError("Phase 7 isolated PostgreSQL acceptance tests failed")
    print(
        "Phase 7 two-writer idempotency, revocation serialization, exact lineage, complete "
        "checks, payload consistency, and append-only PostgreSQL tests passed."
    )


def verify_phase10_postgres_acceptance(environment: dict[str, str]) -> None:
    test_environment = os.environ.copy()
    test_environment["FABLE5_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:"
        f"{environment['POSTGRES_PORT']}/fable5"
    )
    test_environment["FABLE5_CODE_VERSION_GIT_SHA"] = environment["FABLE5_CODE_VERSION_GIT_SHA"]
    test_environment["FABLE5_VERIFY_PHASE"] = "10"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "services/paper/tests/test_phase10_postgres.py", "-q"],
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
        raise AssertionError("Phase 10 isolated PostgreSQL acceptance tests failed")
    print(
        "Phase 10 two-writer idempotency, exact source/transition lineage, complete child "
        "registry, payload parity, deferred completeness, and append-only PostgreSQL tests passed."
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


def verify_phase7_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_7_TABLES
        for trigger_name in (f"{table}_immutable", f"{table}_no_truncate")
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_7_TABLES
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
        + ",".join(f"'{table}'" for table in PHASE_7_TABLES)
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
            f"Phase 7 append-only trigger catalog did not match the migration: {installed_triggers}"
        )

    for table in PHASE_7_TABLES:
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
            raise AssertionError(f"Phase 7 append-only proof has no persisted row in {table}")
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
            raise AssertionError(f"Phase 7 append-only proof found no column in {table}")
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
            if result.returncode == 0 or PHASE_7_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 7 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print(f"Phase 7 append-only trigger proof passed for {len(PHASE_7_TABLES)} tables.")


def verify_phase10_append_only(project: str, environment: dict[str, str]) -> None:
    expected_trigger_names = sorted(
        trigger_name
        for table in PHASE_10_TABLES
        for trigger_name in (f"{table}_immutable", f"{table}_no_truncate")
    )
    expected_triggers = ",".join(
        sorted(
            trigger
            for table in PHASE_10_TABLES
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
        + ",".join(f"'{table}'" for table in PHASE_10_TABLES)
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
            "Phase 10 append-only trigger catalog did not match the migration: "
            + installed_triggers
        )

    for table in PHASE_10_TABLES:
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
            raise AssertionError(f"Phase 10 append-only proof has no persisted row in {table}")
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
            raise AssertionError(f"Phase 10 append-only proof found no column in {table}")
        for statement in (
            f'UPDATE public.{table} SET "{column}" = "{column}";',
            f"DELETE FROM public.{table};",
            f"TRUNCATE public.{table} CASCADE;",
        ):
            result = compose_exec(
                project,
                environment,
                "postgres",
                ["psql", "-U", "fable5", "-d", "fable5", "-v", "ON_ERROR_STOP=1", "-c", statement],
                check=False,
            )
            diagnostic = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0 or PHASE_10_APPEND_ONLY_ERROR not in diagnostic:
                raise AssertionError(
                    "Phase 10 mutation was not rejected by its append-only trigger: "
                    f"{statement} Output: {diagnostic.strip()}"
                )
    print("Phase 10 append-only update/delete/truncate proof passed for all three tables.")


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


def verify_phase7_migration_cycle(
    project: str,
    environment: dict[str, str],
) -> dict[str, tuple[int, str]]:
    earlier_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
        *PHASE_5_TABLES,
        *PHASE_6_TABLES,
    )
    before = snapshot_tables(project, environment, earlier_tables)
    if len(before) != 39:
        raise AssertionError("Phase 7 migration proof did not cover all 39 Phase 1-6 tables")
    empty_earlier_tables = sorted(table for table, (count, _) in before.items() if count < 1)
    if empty_earlier_tables:
        raise AssertionError(
            "Phase 7 migration proof requires preserved evidence in every earlier table: "
            + ", ".join(empty_earlier_tables)
        )
    print(
        "Phase 7 earlier-table snapshots: "
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
            "0006_phase6",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_7_TABLES)
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    expected_downgraded = "0006_phase6|" + "|".join("t" for _ in PHASE_7_TABLES)
    if downgraded != expected_downgraded:
        raise AssertionError(f"Phase 7 downgrade did not remove only Phase 7 tables: {downgraded}")
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, earlier_tables),
        "during downgrade to 0006_phase6",
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
            "0007_phase7",
        ],
        project=project,
        env=environment,
    )
    present_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_7_TABLES)
        + " FROM alembic_version;"
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", present_query],
    ).stdout.strip()
    expected_restored = "0007_phase7|" + "|".join("t" for _ in PHASE_7_TABLES)
    if restored != expected_restored:
        raise AssertionError(f"Phase 7 re-upgrade did not restore revision 0007: {restored}")
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, earlier_tables),
        "during re-upgrade to 0007_phase7",
    )
    print(
        "Phase 7 0007->0006->0007 migration cycle preserved all 39 Phase 1-6 tables "
        "byte-identically."
    )
    return before


def verify_phase7_prior_rows_unchanged(
    project: str,
    environment: dict[str, str],
    expected: dict[str, tuple[int, str]],
) -> None:
    assert_snapshots_equal(
        expected,
        snapshot_tables(project, environment, tuple(expected)),
        "during Phase 7 assessment and revocation APIs",
    )
    print("Phase 7 APIs preserved all 39 Phase 1-6 tables byte-identically.")


def snapshot_pre_phase10_function_bodies(
    project: str,
    environment: dict[str, str],
) -> str:
    query = (
        "SELECT COALESCE(jsonb_agg(jsonb_build_object("
        "'identity', p.oid::regprocedure::text, 'source', p.prosrc, "
        "'kind', p.prokind, 'volatility', p.provolatile) "
        "ORDER BY p.oid::regprocedure::text), '[]'::jsonb)::text "
        "FROM pg_proc AS p JOIN pg_namespace AS n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname NOT LIKE '%phase10%';"
    )
    rendered = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", query],
    ).stdout.strip()
    payload = json.loads(rendered or "[]")
    if not isinstance(payload, list) or not payload:
        raise AssertionError("Phase 10 migration proof found no earlier function bodies")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_phase10_migration_cycle(
    project: str,
    environment: dict[str, str],
) -> dict[str, tuple[int, str]]:
    earlier_tables = (
        "research_audit_events",
        *PHASE_2_TABLES,
        *PHASE_3_TABLES,
        *PHASE_4_TABLES,
        *PHASE_5_TABLES,
        *PHASE_6_TABLES,
        *PHASE_7_TABLES,
    )
    before = snapshot_tables(project, environment, earlier_tables)
    if len(before) != 46:
        raise AssertionError("Phase 10 migration proof did not cover all 46 Phase 1-7 tables")
    empty = sorted(table for table, (count, _) in before.items() if count < 1)
    if empty:
        raise AssertionError(
            "Phase 10 migration proof requires nonempty earlier evidence: " + ", ".join(empty)
        )
    version = compose_exec(
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
            "SELECT version_num FROM alembic_version;",
        ],
    ).stdout.strip()
    if version != "0007_phase7":
        raise AssertionError(f"Phase 10 migration cycle must start at 0007_phase7: {version}")
    functions_before = snapshot_pre_phase10_function_bodies(project, environment)

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0008_phase10",
        ],
        project=project,
        env=environment,
    )
    present_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NOT NULL" for table in PHASE_10_TABLES)
        + ", to_regprocedure('validate_phase10_simulation_completeness()') IS NOT NULL"
        + ", to_regprocedure('reject_phase10_paper_mutation()') IS NOT NULL"
        + " FROM alembic_version;"
    )
    upgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", present_query],
    ).stdout.strip()
    expected_upgraded = "0008_phase10|" + "|".join("t" for _ in range(len(PHASE_10_TABLES) + 2))
    if upgraded != expected_upgraded:
        raise AssertionError(f"Phase 10 upgrade did not install the exact schema: {upgraded}")
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, earlier_tables),
        "during upgrade to 0008_phase10",
    )
    if snapshot_pre_phase10_function_bodies(project, environment) != functions_before:
        raise AssertionError("Phase 10 upgrade changed an earlier function body")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "downgrade",
            "0007_phase7",
        ],
        project=project,
        env=environment,
    )
    absent_query = (
        "SELECT version_num, "
        + ", ".join(f"to_regclass('public.{table}') IS NULL" for table in PHASE_10_TABLES)
        + ", to_regprocedure('validate_phase10_simulation_completeness()') IS NULL"
        + ", to_regprocedure('reject_phase10_paper_mutation()') IS NULL"
        + " FROM alembic_version;"
    )
    downgraded = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", absent_query],
    ).stdout.strip()
    expected_downgraded = "0007_phase7|" + "|".join("t" for _ in range(len(PHASE_10_TABLES) + 2))
    if downgraded != expected_downgraded:
        raise AssertionError(f"Phase 10 downgrade left Phase 10 objects: {downgraded}")
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, earlier_tables),
        "during downgrade to 0007_phase7",
    )
    if snapshot_pre_phase10_function_bodies(project, environment) != functions_before:
        raise AssertionError("Phase 10 downgrade changed an earlier function body")

    run(
        [
            "exec",
            "-T",
            "api",
            "alembic",
            "-c",
            "services/api/alembic.ini",
            "upgrade",
            "0008_phase10",
        ],
        project=project,
        env=environment,
    )
    restored = compose_exec(
        project,
        environment,
        "postgres",
        ["psql", "-U", "fable5", "-d", "fable5", "-tAc", present_query],
    ).stdout.strip()
    if restored != expected_upgraded:
        raise AssertionError(f"Phase 10 re-upgrade did not restore exact objects: {restored}")
    assert_snapshots_equal(
        before,
        snapshot_tables(project, environment, earlier_tables),
        "during re-upgrade to 0008_phase10",
    )
    if snapshot_pre_phase10_function_bodies(project, environment) != functions_before:
        raise AssertionError("Phase 10 re-upgrade changed an earlier function body")
    print(
        "Phase 10 0007->0008->0007->0008 cycle preserved all 46 nonempty Phase 1-7 "
        "tables and every earlier public function body byte-identically."
    )
    return before


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


def phase10_acceptance_resource_inventory(environment: dict[str, str]) -> list[str]:
    commands = (
        (
            "container",
            [
                "docker",
                "ps",
                "--all",
                "--filter",
                "name=fable5_acceptance_",
                "--format",
                "{{.Names}}",
            ],
        ),
        (
            "network",
            [
                "docker",
                "network",
                "ls",
                "--filter",
                "name=fable5_acceptance_",
                "--format",
                "{{.Name}}",
            ],
        ),
        (
            "volume",
            [
                "docker",
                "volume",
                "ls",
                "--filter",
                "name=fable5_acceptance_",
                "--format",
                "{{.Name}}",
            ],
        ),
    )
    resources: list[str] = []
    for kind, command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        resources.extend(f"{kind}:{name}" for name in result.stdout.splitlines() if name)
    return resources


def verify_phase10_acceptance_resource_namespace(
    stage: str,
    environment: dict[str, str],
) -> None:
    resources = phase10_acceptance_resource_inventory(environment)
    if resources:
        raise AssertionError(
            f"Phase 10 {stage} found verifier resources with ambiguous cleanup ownership: "
            + ", ".join(resources)
        )
    print(f"Phase 10 verifier resource namespace ({stage}) is empty.")


def verify_phase9_compose_cleanup(project: str, environment: dict[str, str]) -> None:
    commands = (
        (
            "containers",
            [
                "docker",
                "ps",
                "--all",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.Names}}",
            ],
        ),
        (
            "networks",
            [
                "docker",
                "network",
                "ls",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.Name}}",
            ],
        ),
        (
            "volumes",
            [
                "docker",
                "volume",
                "ls",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.Name}}",
            ],
        ),
    )
    remaining: list[str] = []
    for kind, command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        remaining.extend(f"{kind}:{name}" for name in result.stdout.splitlines() if name)
    if remaining:
        raise AssertionError("Phase 9 verifier cleanup left resources: " + ", ".join(remaining))


def verify_compose(phase: int = 1) -> None:
    phase10_identity = phase10_clean_git_identity("preflight") if phase == 10 else None
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required for full verification; use --static-only otherwise.")
    if phase == 10:
        verify_phase10_acceptance_resource_namespace("preflight", os.environ.copy())

    project = f"fable5_acceptance_{uuid.uuid4().hex[:8]}"
    if phase10_identity is None:
        environment, api_url, frontend_url = acceptance_environment(phase)
    else:
        environment, api_url, frontend_url = acceptance_environment(
            phase,
            expected_git_identity=phase10_identity,
        )
    try:
        with phase9_stage(phase, "compose_startup"):
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
            with phase9_stage(phase, "phase2_acceptance"):
                queue_evidence = verify_phase2_api(api_url)
                verify_phase2_queue_processing(project, environment, queue_evidence)
                verify_phase2_append_only(project, environment)
            if phase == 2:
                verify_phase2_migration_cycle(project, environment)
                print("Full Compose Phase 2 verification passed.")
            else:
                with phase9_stage(phase, "phase3_acceptance"):
                    phase3_card_id = verify_phase3_api(api_url)
                    verify_phase3_changed_rule_version(project, environment, phase3_card_id)
                    verify_phase3_postgres_acceptance(environment)
                    verify_phase3_append_only(project, environment)
                if phase == 3:
                    verify_phase3_migration_cycle(project, environment)
                    print("Full Compose Phase 3 verification passed.")
                else:
                    with phase9_stage(phase, "phase4_acceptance"):
                        phase4_snapshot_id = verify_phase4_api(api_url)
                        verify_phase4_postgres_acceptance(environment)
                    if phase == 4:
                        verify_phase4_migration_cycle(project, environment)
                        print("Full Compose Phase 4 verification passed.")
                    else:
                        with phase9_stage(phase, "phase5_acceptance"):
                            verify_phase5_api(api_url, phase4_snapshot_id)
                            verify_phase5_postgres_acceptance(environment)
                            verify_phase5_append_only(project, environment)
                        if phase == 5:
                            verify_phase5_migration_cycle(project, environment)
                            print("Full Compose Phase 5 verification passed.")
                        else:
                            with phase9_stage(phase, "phase6_acceptance"):
                                # Run the reversible cycle before Phase 6 creates additive Phase 4
                                # record types, whose downgrade guard intentionally fails closed.
                                with phase9_stage(phase, "phase6_schema_cycle"):
                                    verify_phase6_migration_cycle(project, environment)
                                    if phase >= 7:
                                        run(
                                            [
                                                "exec",
                                                "-T",
                                                "api",
                                                "alembic",
                                                "-c",
                                                "services/api/alembic.ini",
                                                "upgrade",
                                                "0007_phase7",
                                            ],
                                            project=project,
                                            env=environment,
                                        )
                                with phase9_stage(phase, "phase6_api"):
                                    with phase6_request_timeout_context(phase):
                                        phase6_run_ids = verify_phase6_api(api_url)
                                with phase9_stage(phase, "phase6_postgres_tests"):
                                    verify_phase6_postgres_acceptance(environment)
                                with phase9_stage(phase, "phase6_append_only"):
                                    verify_phase6_append_only(project, environment)
                            if phase == 6:
                                print("Full Compose Phase 6 verification passed.")
                            else:
                                with phase9_stage(phase, "phase7_acceptance"):
                                    prior_rows = verify_phase7_migration_cycle(project, environment)
                                    phase7_evidence = verify_phase7_api(
                                        project,
                                        environment,
                                        api_url,
                                        phase6_run_ids,
                                    )
                                    verify_phase7_postgres_acceptance(environment)
                                    verify_phase7_append_only(project, environment)
                                    verify_phase7_prior_rows_unchanged(
                                        project,
                                        environment,
                                        prior_rows,
                                    )
                                if phase == 7:
                                    print("Full Compose Phase 7 verification passed.")
                                else:
                                    with phase9_stage(phase, "phase8_acceptance"):
                                        if set(phase7_evidence) != {
                                            "positive_assessment_id",
                                            "positive_artifact_sha256",
                                            "revocation_id",
                                        }:
                                            raise AssertionError(
                                                "Phase 8 did not receive complete Phase 7 "
                                                "artifact identities"
                                            )
                                        with phase9_stage(phase, "phase8_timeline_api"):
                                            verify_phase8_evidence_timeline_api(api_url)
                                        if phase in {8, 9, 10}:
                                            verify_phase8_browser(
                                                project,
                                                environment,
                                                frontend_url,
                                            )
                                            print("Full Compose Phase 8 verification passed.")
                                    if phase == 10:
                                        with phase9_stage(phase, "phase10_acceptance"):
                                            with phase9_stage(phase, "phase10_schema_cycle"):
                                                verify_phase10_migration_cycle(
                                                    project,
                                                    environment,
                                                )
                                            with phase9_stage(phase, "phase10_api"):
                                                verify_phase10_api(
                                                    project,
                                                    environment,
                                                    api_url,
                                                    phase6_run_ids,
                                                    phase7_evidence["positive_assessment_id"],
                                                )
                                            with phase9_stage(
                                                phase,
                                                "phase10_postgres_tests",
                                            ):
                                                verify_phase10_postgres_acceptance(environment)
                                            with phase9_stage(
                                                phase,
                                                "phase10_append_only",
                                            ):
                                                verify_phase10_append_only(
                                                    project,
                                                    environment,
                                                )
                                            with phase9_stage(phase, "phase10_browser"):
                                                verify_phase10_browser(
                                                    project,
                                                    environment,
                                                    frontend_url,
                                                )
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
        try:
            with phase9_stage(phase, "compose_cleanup"):
                cleanup = subprocess.run(
                    ["docker", "compose", "--project-name", project, "down", "--volumes"],
                    cwd=ROOT,
                    check=False,
                    text=True,
                    env=environment,
                )
                if phase in {9, 10}:
                    if cleanup.returncode != 0:
                        raise AssertionError(
                            f"Phase {phase} inherited Compose cleanup exited {cleanup.returncode}"
                        )
                    if phase == 9:
                        verify_phase9_compose_cleanup(project, environment)
        finally:
            try:
                if phase == 10:
                    verify_phase10_acceptance_resource_namespace("post-cleanup", environment)
            finally:
                if phase10_identity is not None:
                    phase10_clean_git_identity("post-cleanup", expected=phase10_identity)

    if phase == 9:
        print("Full Compose Phase 9 verification passed.")
    if phase == 10:
        print("Full Compose Phase 10 verification passed.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify phase-aware repository policy and services."
    )
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "--phase",
        type=phase_number,
        default=os.environ.get("FABLE5_VERIFY_PHASE", "10"),
        help=(
            "Apply repository policy checks for phase 1, 2, 3, 4, 5, 6, 7, 8, 9, or 10 "
            "(default: FABLE5_VERIFY_PHASE or 10)."
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
