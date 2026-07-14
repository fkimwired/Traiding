from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    raise AssertionError(f"missing {class_name}")


def test_hard_gates_are_exact_file_prefixes() -> None:
    prompt = normalized(ROOT / "FABLE5_BUILD_PROMPT.md")
    start_marker = "1. **No live trading. Paper trading only.**"
    end_marker = "   are configured; never invent real results."
    start = prompt.index(start_marker)
    end = prompt.index(end_marker, start) + len(end_marker)
    gates = prompt[start:end]

    assert hashlib.sha256(gates.encode()).hexdigest() == (
        "1c6586b54c77c5a9df8e9838638631127cb2e5bc0af1c813b27b7f6af355d672"
    )
    for filename in ("AGENTS.md", "CLAUDE.md"):
        assert normalized(ROOT / filename).startswith(gates + "\n\n")


def test_research_supplement_copy_is_exact() -> None:
    assert normalized(ROOT / "RESEARCH_SUPPLEMENT.md") == normalized(
        ROOT / "docs" / "RESEARCH_SUPPLEMENT.md"
    )


def test_baseline_migration_is_reversible_and_non_empty() -> None:
    migration = ROOT / "services/api/migrations/versions/0001_phase1_audit_spine.py"
    tree = ast.parse(migration.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "upgrade" in functions
    assert "downgrade" in functions
    assert len(functions["upgrade"].body) > 1
    assert len(functions["downgrade"].body) > 1
    assert "create_all" not in migration.read_text(encoding="utf-8")


def test_audit_migration_blocks_row_mutations_and_truncate() -> None:
    migration = ROOT / "services/api/migrations/versions/0001_phase1_audit_spine.py"
    source = migration.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sql = " ".join(
        " ".join(node.value.split())
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )

    assert "BEFORE UPDATE OR DELETE ON research_audit_events FOR EACH ROW" in sql
    assert "BEFORE TRUNCATE ON research_audit_events FOR EACH STATEMENT" in sql
    assert (
        "DROP TRIGGER IF EXISTS research_audit_events_no_truncate ON research_audit_events"
    ) in sql
    assert (
        "DROP TRIGGER IF EXISTS research_audit_events_immutable ON research_audit_events"
    ) in sql
    assert source.rindex("research_audit_events_no_truncate") < (
        source.index("DROP FUNCTION IF EXISTS reject_audit_event_mutation()")
    )
    assert source.rindex("research_audit_events_immutable") < (
        source.index("DROP FUNCTION IF EXISTS reject_audit_event_mutation()")
    )


def test_phase2_migration_is_reversible_append_only_and_preserves_phase1_parent() -> None:
    migration = ROOT / "services/api/migrations/versions/0002_phase2_source_extraction.py"
    source = migration.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = {
        node.target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0002_phase2"
    assert assignments["down_revision"] == "0001_phase1"
    assert "create_all" not in source
    for table in (
        "research_sources",
        "research_source_versions",
        "research_source_version_corroborations",
        "extraction_requests",
        "extraction_events",
        "trading_idea_cards",
        "card_official_corroborations",
        "research_memos",
    ):
        assert f'"{table}"' in source
    assert "CREATE TRIGGER {table}_immutable" in source
    assert "CREATE TRIGGER {table}_no_truncate" in source
    assert "DROP TRIGGER IF EXISTS {table}_immutable" in source
    assert "DROP TRIGGER IF EXISTS {table}_no_truncate" in source
    supply_time_column = source.split('"supplied_at_utc"', 1)[1].split(
        'sa.Column("retrieved_at_utc"', 1
    )[0]
    assert 'server_default=sa.text("CURRENT_TIMESTAMP")' in supply_time_column

    repository = normalized(ROOT / "services/extraction/src/fable5_extraction/repository.py")
    version_insert = repository.split("INSERT INTO research_source_versions", 1)[1].split(
        "RETURNING *", 1
    )[0]
    assert "supplied_at_utc" not in version_insert


def test_phase4_entrypoints_and_images_select_the_active_phase() -> None:
    assert "--phase 4" in normalized(ROOT / "scripts/check.ps1")
    assert "--phase 4" in normalized(ROOT / "scripts/check.sh")
    assert "--phase 4" in normalized(ROOT / "Makefile")
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.count("--phase 4") >= 2
    for dockerfile in ("services/api/Dockerfile", "services/jobs/Dockerfile"):
        assert "COPY services/extraction ./services/extraction" in normalized(ROOT / dockerfile)
        assert "COPY services/data ./services/data" in normalized(ROOT / dockerfile)
    assert "COPY services/mapping ./services/mapping" in normalized(
        ROOT / "services/api/Dockerfile"
    )


def test_phase2_full_verifier_proves_enabled_triggers_before_cascade_mutations() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    assert "FROM pg_trigger AS t" in verifier
    assert "t.tgenabled IN ('O','A')" in verifier
    assert 'f"TRUNCATE public.{table} CASCADE;"' in verifier
    assert "Phase 2 append-only trigger proof passed" in verifier


def test_phase2_openapi_has_no_later_phase_or_execution_surface() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    paths = {path: methods for path, methods in schema["paths"].items() if path.startswith("/v1/")}
    assert paths
    assert all(set(methods) <= {"get", "post"} for methods in paths.values())
    rendered = " ".join(paths).lower()
    for forbidden in ("signal", "strategy", "backtest", "broker", "position", "order", "live"):
        assert forbidden not in rendered

    dependencies = normalized(ROOT / "pyproject.toml").lower()
    for forbidden_dependency in ("alpaca-py", "ib_insync", "ibapi", "ccxt"):
        assert forbidden_dependency not in dependencies
    assert list((ROOT / "services/backtester").iterdir()) == [
        ROOT / "services/backtester/README.md"
    ]
    assert list((ROOT / "services/risk").iterdir()) == [ROOT / "services/risk/README.md"]


def test_phase3_handoff_has_closed_verdicts_and_all_required_sections() -> None:
    handoff = normalized(ROOT / "docs/handoffs/PHASE_03.md")
    expected_headings = [
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
    assert re.findall(r"^## .+$", handoff, flags=re.MULTILINE) == expected_headings

    contract = handoff.split("## Contracts and invariants", 1)[1].split(
        "## Implementation units", 1
    )[0]
    vocabulary_table = contract.split("Priority prose", 1)[0]
    verdicts = set(re.findall(r"`([A-Z][A-Z_]+)`", vocabulary_table))
    assert verdicts == {
        "BUILD_RESEARCH",
        "DEFER",
        "DEFER_READ_ONLY",
        "REJECT_PLATFORM",
        "NON_TESTABLE",
    }
    assert "`REJECT`" not in contract
    for required_mapping in (
        "| 1 | `testability_status=non_testable` or ambiguous family | `NON_TESTABLE` |",
        "| 2 | E — order-flow, order-book, scalp, sub-minute, or HFT | `REJECT_PLATFORM` |",
        "| 3 | C — social/news with contribution blocked | `DEFER` |",
        "| 4 | D — pairs/statistical arbitrage | `DEFER` |",
        "| 5 | F — options-flow/IV-versus-RV analytics | `DEFER_READ_ONLY` |",
        "| 6 | A, B, or corroboration-eligible C | `BUILD_RESEARCH` |",
        "`OFFICIAL_CORROBORATION_REQUIRED`",
    ):
        assert required_mapping in contract

    for later_state in (
        "PASS_RESEARCH",
        "FAIL_REJECT",
        "BLOCKED_MISSING_POLICY",
        "APPROVED_PAPER",
    ):
        assert later_state not in handoff
    for command in (
        ".\\scripts\\check.ps1",
        ".\\scripts\\test.ps1",
        "npm run build",
        "scripts\\verify_phase1.py --static-only --phase 3",
        "scripts\\verify_phase1.py --phase 3",
    ):
        assert command in handoff

    canon_rules = normalized(ROOT / "docs/STRATEGY_CANON.md").split(
        "## Deterministic verdict rules for Phase 3", 1
    )[1]
    for verdict in verdicts:
        assert f"`{verdict}`" in canon_rules
    assert "`REJECT`" not in canon_rules


def test_phase3_artifacts_and_migration_are_scoped_reversible_and_append_only() -> None:
    required_paths = (
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
        "services/frontend/src/app/ideas/IdeaMappings.tsx",
    )
    assert all((ROOT / path).is_file() for path in required_paths)
    assert any((ROOT / "services/mapping/tests").glob("test_*.py"))

    migration = ROOT / "services/api/migrations/versions/0003_phase3_canon_mapping.py"
    source = migration.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = {
        node.target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0003_phase3"
    assert assignments["down_revision"] == "0002_phase2"
    assert "create_all" not in source
    for table in (
        "research_mapping_versions",
        "mapping_official_corroborations",
        "mapping_rationale_artifacts",
    ):
        assert f'"{table}"' in source
    for invariant in (
        "mapper_rule_set_version",
        "mapper_rule_set_sha256",
        "matched_rule_ids",
        "reason_codes",
        "validate_phase3_mapping_lineage",
        "research_mapping_versions_corroboration_set",
        "mapping_official_corroborations_exact_set",
        "card_official_corroborations_mapping_set",
        "DEFERRABLE INITIALLY DEFERRED",
        "reject_phase3_finalized_corroboration_append",
        "card_official_corroborations_phase3_finalized",
        "mapping_official_corroborations_phase3_finalized",
        "CREATE TRIGGER {table}_immutable",
        "CREATE TRIGGER {table}_no_truncate",
        "DROP TRIGGER IF EXISTS {table}_immutable",
        "DROP TRIGGER IF EXISTS {table}_no_truncate",
        "Phase 3 mapping records are append-only",
    ):
        assert invariant in source


def test_phase3_openapi_mapping_surface_and_generated_contract_are_exact() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    components = schema["components"]["schemas"]
    mapping_paths = {
        path: {
            method for method in operations if method in {"get", "post", "put", "patch", "delete"}
        }
        for path, operations in schema["paths"].items()
        if "mapping" in path
    }
    assert mapping_paths == {
        "/v1/cards/{card_id}/mappings": {"post"},
        "/v1/mappings": {"get"},
        "/v1/mappings/{mapping_id}": {"get"},
    }
    assert "requestBody" not in schema["paths"]["/v1/cards/{card_id}/mappings"]["post"]

    assert set(components["CanonicalFamily"]["enum"]) == {
        "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "B_TIME_SERIES_MOMENTUM_REGIME",
        "C_OFFICIAL_EVENT_TEXT_OVERLAY",
        "D_PAIRS_STATISTICAL_ARBITRAGE",
        "E_ORDER_BOOK_MICROSTRUCTURE",
        "F_OPTIONS_FLOW_IV_RV_ANALYTICS",
    }
    assert set(components["ResearchVerdict"]["enum"]) == {
        "BUILD_RESEARCH",
        "DEFER",
        "DEFER_READ_ONLY",
        "REJECT_PLATFORM",
        "NON_TESTABLE",
    }
    model_reasons = enum_string_values(
        ROOT / "services/mapping/src/fable5_mapping/models.py", "MappingReasonCode"
    )
    assert {
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
    } <= model_reasons
    assert set(components["MappingReasonCode"]["enum"]) == model_reasons
    model_rule_ids = enum_string_values(
        ROOT / "services/mapping/src/fable5_mapping/models.py", "MappingRuleId"
    )
    assert set(components["MappingRuleId"]["enum"]) == model_rule_ids

    mapping = components["ResearchMapping"]
    assert {
        "canonical_family",
        "verdict",
        "matched_rule_ids",
        "reason_codes",
        "mapper_rule_set_version",
        "mapper_rule_set_sha256",
    } <= set(mapping["required"])
    rendered_mapping = json.dumps(mapping["properties"])
    for component in (
        "CanonicalFamily",
        "ResearchVerdict",
        "MappingRuleId",
        "MappingReasonCode",
    ):
        assert f"#/components/schemas/{component}" in rendered_mapping
    assert mapping["properties"]["mapper_rule_set_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    nested = components["MappingWithRationale"]["properties"]
    assert nested["mapping"] == {"$ref": "#/components/schemas/ResearchMapping"}
    assert "rationale" in nested

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    assert "MappingWithRationale:" in generated
    assert "ResearchMapping:" in generated

    domain_paths = {
        path: operations for path, operations in schema["paths"].items() if path.startswith("/v1/")
    }
    assert all(
        {method for method in operations if method in {"get", "post", "put", "patch", "delete"}}
        <= {"get", "post"}
        for operations in domain_paths.values()
    )
    rendered_paths = " ".join(domain_paths).lower()
    for forbidden in ("signal", "backtest", "broker", "position", "order", "live", "paper"):
        assert forbidden not in rendered_paths


def test_phase3_full_verifier_has_fixture_precedence_triggers_and_preserving_cycle() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    mapper_source = normalized(ROOT / "services/mapping/src/fable5_mapping/mapper.py")
    mapper_sha256 = hashlib.sha256(mapper_source.encode("utf-8")).hexdigest()
    rules_source = normalized(ROOT / "services/mapping/src/fable5_mapping/rules.py")
    assert "fable5_mapping.mapper.sha256:" in rules_source
    assert mapper_sha256 in rules_source
    assert "assigned_call_keyword" in verifier
    assert (
        "PHASE_3_RULE_SET_SHA256 = "
        '"352afeee889857834f7453f2d37bbb6b40e414ac4da9befccce476cc2061674a"'
    ) in verifier
    tree = ast.parse(verifier)
    matrix = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PHASE_3_FIXTURE_MATRIX"
    )
    assert matrix == {
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

    compose_branch = verifier.split("def verify_compose", 1)[1]
    assert "if phase == 2:\n                verify_phase2_migration_cycle" in compose_branch
    for preserved_phase3_gate in (
        "phase3_card_id = verify_phase3_api(api_url)",
        "verify_phase3_changed_rule_version(project, environment, phase3_card_id)",
        "verify_phase3_postgres_acceptance(environment)",
        "verify_phase3_append_only(project, environment)",
        "if phase == 3:\n                    verify_phase3_migration_cycle",
    ):
        assert preserved_phase3_gate in compose_branch
    phase2_cycle = verifier.split("def verify_phase2_migration_cycle", 1)[1].split(
        "def verify_phase3_migration_cycle", 1
    )[0]
    assert '"upgrade",\n            "0002_phase2"' in phase2_cycle
    for evidence in (
        "t.tgenabled IN ('O','A')",
        'f"TRUNCATE public.{table} CASCADE;"',
        "Phase 3 append-only trigger proof passed",
        "Phase 3 lineage, exact corroboration-set, and two-writer PostgreSQL tests passed",
        "HFT rejection mapping changed the API surface or created a scaffold",
        "snapshot_tables",
        'earlier_tables = ("research_audit_events", *PHASE_2_TABLES)',
        '"downgrade",\n            "0002_phase2"',
        'downgraded != "0002_phase2|t|t|t"',
        'restored != "0003_phase3|t|t|t"',
        "assert_snapshots_equal(before, after_downgrade",
        "assert_snapshots_equal(before, after_reupgrade",
    ):
        assert evidence in verifier


def test_phase4_verifier_has_static_contract_isolation_live_gate_and_preserving_cycle() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")

    for static_evidence in (
        "PHASE_4_REQUIRED_PATHS",
        "PHASE_4_CAPABILITIES",
        "PHASE_4_RECORD_TYPES",
        "PHASE_4_SCHEMA_VERSIONS",
        "PHASE_1_3_MIGRATION_SHA256",
        "FORBIDDEN_VENDOR_SDK_MODULES",
        "FORBIDDEN_PHASE_4_NETWORK_MODULES",
        "PHASE_5_SYMBOL_PREFIXES",
        "SnapshotCreateRequest accepts fields beyond server-resolvable identities",
        "Phase 4 credential-unavailable zero-network evidence is missing",
        "Default Phase 4 workflow does not server-resolve mapping-bound synthetic",
        "Forbidden Phase 5+ or execution API path",
    ):
        assert static_evidence in verifier

    compose_branch = verifier.split("def verify_compose", 1)[1]
    for compose_gate in (
        "verify_phase4_api(api_url)",
        "verify_phase4_postgres_acceptance(environment)",
        "verify_phase4_migration_cycle(project, environment)",
    ):
        assert compose_gate in compose_branch
    for full_gate in (
        "tests/test_phase4_postgres.py",
        "Phase 4 authorized A/B/C create/read/list",
        "all-seven-table append-only PostgreSQL tests passed",
    ):
        assert full_gate in verifier

    phase4_cycle = verifier.split("def verify_phase4_migration_cycle", 1)[1].split(
        "def wait_for_frontend", 1
    )[0]
    for preservation_evidence in (
        'earlier_tables = ("research_audit_events", *PHASE_2_TABLES, *PHASE_3_TABLES)',
        "phase4_migration_preservation_fixture",
        "len(before) != 12",
        "empty_earlier_tables",
        '"downgrade",\n            "0003_phase3"',
        '"upgrade",\n            "0004_phase4"',
        "assert_snapshots_equal(before, after_downgrade",
        "assert_snapshots_equal(before, after_reupgrade",
        "preserved all 12 Phase 1-3 tables",
    ):
        assert preservation_evidence in phase4_cycle
