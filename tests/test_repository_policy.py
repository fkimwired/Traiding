from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


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
