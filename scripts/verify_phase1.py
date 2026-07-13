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
        raise argparse.ArgumentTypeError("phase must be 1, 2, or 3") from exc
    if phase not in {1, 2, 3}:
        raise argparse.ArgumentTypeError("phase must be 1, 2, or 3")
    return phase


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


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
            if "--phase 3" not in normalized(ROOT / entrypoint):
                raise AssertionError(f"{entrypoint} does not select the Phase 3 verifier")
        if normalized(ROOT / ".github/workflows/ci.yml").count("--phase 3") < 2:
            raise AssertionError("CI does not run both static and full Phase 3 verification")

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
        for dormant_directory in ("services/backtester", "services/risk", "strategy_specs"):
            entries = sorted(path.name for path in (ROOT / dormant_directory).iterdir())
            if entries != ["README.md"]:
                raise AssertionError(f"Phase 3 created a forbidden scaffold in {dormant_directory}")

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


def acceptance_environment() -> tuple[dict[str, str], str, str]:
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
) -> dict[str, object] | list[object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status not in {200, 201, 202}:
            raise AssertionError(f"{method} {url} returned {response.status}")
        if "application/json" not in response.headers.get("content-type", ""):
            raise AssertionError(f"{method} {url} did not return JSON")
        return json.load(response)


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
        ["exec", "-T", "api", "alembic", "-c", "services/api/alembic.ini", "upgrade", "head"],
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
    environment, api_url, frontend_url = acceptance_environment()
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
                verify_phase3_migration_cycle(project, environment)
                print("Full Compose Phase 3 verification passed.")
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
        default=os.environ.get("FABLE5_VERIFY_PHASE", "1"),
        help=(
            "Apply repository policy checks for phase 1, 2, or 3 "
            "(default: FABLE5_VERIFY_PHASE or 1)."
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
