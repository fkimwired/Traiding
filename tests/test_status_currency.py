from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.verify_phase1 import GATE_SHA256, canonical_gates, normalized

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_ROOT = ROOT / "docs/handoffs"
README = ROOT / "README.md"
T010_BASELINE_SHA = "4180ce659aa621d6155cac1118f7011deb92aa9f"
PINNED_GATE_SHA256 = "1c6586b54c77c5a9df8e9838638631127cb2e5bc0af1c813b27b7f6af355d672"
EXTERNAL_RULES_HEADING = "# External observation and free-source rules"
EXTERNAL_RULES_SHA256 = "dae3a082ef1c5427d63ab3c2732c0a0e2cc0fae57854d6ef3569d26a13c44b99"
LEGACY_PHASE27_STATUS_ENTRY_SHA256 = (
    "8d545f9f93b57214bffa8bb221d6c3147ef997e162a1ea6c5ecb1c071a69249f"
)
HANDOFF_NAME = re.compile(r"^PHASE_(0*[1-9]\d*)\.md$")
NEXT_STEP_HEADING = re.compile(
    r"^ {0,3}##[ \t]+Next[ \t]+step(?:[ \t]+#+)?[ \t]*$",
    re.MULTILINE,
)
H2_HEADING = re.compile(r"^ {0,3}##(?=[ \t]|$).*$", re.MULTILINE)
H1_HEADING = re.compile(r"^# .+$", re.MULTILINE)
FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
PHASE_STATUS_START = re.compile(
    r"^[ \t]{0,3}(?:[-*+][ \t]+)?Phase\s+0*([1-9]\d*)\b",
    re.IGNORECASE | re.MULTILINE,
)
ACCEPTED_STATUS = re.compile(
    r"[ \t]{0,3}(?:[-*+][ \t]+)?Phase\s+0*[1-9]\d*\s+is\s+"
    r"formally\s+accepted\s+at\s+commit\s+`(?P<commit>[0-9a-f]{40})`,\s+"
    r"tree\s+`(?P<tree>[0-9a-f]{40})`,\s+with\s+same-SHA\s+"
    r"(?:Ubuntu\s+)?workflow\s+run\s+`(?P<run>\d+)`\.\s*",
    re.IGNORECASE,
)
TRUTHFUL_CURRENT_RESULT = re.compile(
    r"[ \t]{0,3}(?:[-*+][ \t]+)?Phase\s+0*[1-9]\d*\s+"
    r"truthful\s+current\s+result\s+is\s+`BLOCKED\s*/\s*"
    r"(?P<determination>[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)`\.\s*$",
    re.IGNORECASE | re.MULTILINE,
)
PLACEHOLDER_DETERMINATION_ROOTS = frozenset(
    {
        "DUMMY",
        "EXAMPLE",
        "FAKE",
        "FALSE",
        "HYPOTHETICAL",
        "ILLUSTRATIVE",
        "NONE",
        "NOT_SET",
        "NULL",
        "N_A",
        "PENDING",
        "PLACEHOLDER",
        "SAMPLE",
        "SENTINEL",
        "TBD",
        "TEST",
        "TODO",
        "TO_BE_DETERMINED",
        "UNKNOWN",
        "UNSPECIFIED",
    }
)
HYPOTHETICAL_LANGUAGE = re.compile(
    r"\b(?:if|when|unless|once|provided|pending|subject\s+to|only\s+if|"
    r"after\s+approval|upon\s+approval|hypothetical(?:ly)?|false|not\s+true|"
    r"only\s+as\s+an\s+example|for\s+example|example\s+only|illustrative|"
    r"supposedly|purportedly)\b",
    re.IGNORECASE,
)


def without_fenced_code(text: str) -> str:
    visible: list[str] = []
    fence_character: str | None = None
    minimum_fence_length = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence_character is None:
            opening = FENCE_OPEN.match(content)
            if opening is None:
                visible.append(line)
                continue
            marker = opening.group(1)
            fence_character = marker[0]
            minimum_fence_length = len(marker)
        elif re.fullmatch(
            rf"[ \t]{{0,3}}{re.escape(fence_character)}"
            rf"{{{minimum_fence_length},}}[ \t]*",
            content,
        ):
            fence_character = None
            minimum_fence_length = 0
        visible.append("\n" if line.endswith(("\n", "\r")) else "")
    assert fence_character is None, "Unclosed fenced code block"
    return "".join(visible)


def without_html_comments(text: str) -> str:
    visible = HTML_COMMENT.sub(
        lambda match: "\n" * match.group(0).count("\n"),
        text,
    )
    assert "<!--" not in visible and "-->" not in visible, "Malformed HTML comment"
    return visible


def visible_markdown(text: str) -> str:
    return without_fenced_code(without_html_comments(text))


def highest_handoff_phase(handoff_root: Path) -> int:
    phases: list[int] = []
    for path in handoff_root.iterdir():
        if not path.name.startswith("PHASE_"):
            continue
        match = HANDOFF_NAME.fullmatch(path.name)
        assert match is not None, f"Malformed phase handoff filename: {path.name}"
        assert path.is_file() and not path.is_symlink(), (
            f"Phase handoff must be a regular file: {path.name}"
        )
        phase = int(match.group(1))
        assert path.name == f"PHASE_{phase:02d}.md", (
            f"Phase handoff is not canonically named: {path.name}"
        )
        phases.append(phase)
    assert phases, "No phase handoffs found"
    assert len(phases) == len(set(phases)), "Duplicate numeric phase handoff"
    return max(phases)


def next_step_section(readme: str) -> str:
    readme = visible_markdown(readme)
    headings = list(NEXT_STEP_HEADING.finditer(readme))
    assert len(headings) == 1, "README must contain exactly one ## Next step heading"
    start = headings[0].end()
    following = H2_HEADING.search(readme, start)
    end = following.start() if following else len(readme)
    section = readme[start:end]
    assert section.strip(), "README ## Next step section is empty"
    return section


def positive_status_phases(section: str) -> set[int]:
    prose = visible_markdown(section)
    phases: set[int] = set()
    for paragraph in PARAGRAPH_BREAK.split(prose):
        starts = list(PHASE_STATUS_START.finditer(paragraph))
        if not starts:
            continue
        clean_status_chain = not paragraph[: starts[0].start()].strip()
        for index, start in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(paragraph)
            entry = paragraph[start.start() : end]
            phase = int(start.group(1))
            legacy_phase27_entry = (
                phase == 27
                and hashlib.sha256(" ".join(entry.split()).encode()).hexdigest()
                == LEGACY_PHASE27_STATUS_ENTRY_SHA256
            )
            accepted = ACCEPTED_STATUS.fullmatch(entry.strip())
            current_result = TRUTHFUL_CURRENT_RESULT.fullmatch(entry.strip())
            accepted_identity_is_structural = accepted is not None and (
                int(accepted.group("run")) > 0
                and len(set(accepted.group("commit").lower())) >= 8
                and len(set(accepted.group("tree").lower())) >= 8
            )
            current_determination_is_structural = current_result is not None and not any(
                current_result.group("determination").upper() == root
                or current_result.group("determination").upper().startswith(f"{root}_")
                for root in PLACEHOLDER_DETERMINATION_ROOTS
            )
            entry_is_structural = not HYPOTHETICAL_LANGUAGE.search(entry) and (
                accepted_identity_is_structural
                or current_determination_is_structural
                or legacy_phase27_entry
            )
            if clean_status_chain and entry_is_structural:
                phases.add(phase)
            else:
                clean_status_chain = False
    return phases


def assert_status_current(readme_path: Path, handoff_root: Path) -> None:
    expected = highest_handoff_phase(handoff_root)
    positive = positive_status_phases(next_step_section(normalized(readme_path)))
    assert positive, "README contains no positive phase-status statement"
    assert max(positive) == expected, (
        f"README ## Next step highest positive phase is {max(positive)}, "
        f"but highest handoff is Phase {expected}"
    )


def h1_section(text: str, heading: str) -> str:
    matches = [match for match in H1_HEADING.finditer(text) if match.group(0) == heading]
    assert len(matches) == 1, f"{heading!r} must appear exactly once"
    start = matches[0].start()
    following = H1_HEADING.search(text, matches[0].end())
    end = following.start() if following else len(text)
    return text[start:end]


def assert_external_rules_are_verbatim(agents: str, claude: str) -> None:
    expected = h1_section(agents, EXTERNAL_RULES_HEADING)
    actual = h1_section(claude, EXTERNAL_RULES_HEADING)
    assert actual == expected
    assert claude.endswith(expected)


def test_readme_next_step_matches_the_highest_canonical_handoff() -> None:
    assert_status_current(README, HANDOFF_ROOT)


def test_status_currency_rejects_a_newer_handoff_without_positive_readme_status(
    tmp_path: Path,
) -> None:
    current = highest_handoff_phase(HANDOFF_ROOT)
    planted = current + 1
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    source = HANDOFF_ROOT / f"PHASE_{current:02d}.md"
    copied = handoffs / source.name
    shutil.copyfile(source, copied)
    copied.rename(handoffs / f"PHASE_{planted:02d}.md")
    with pytest.raises(AssertionError, match=rf"highest handoff is Phase {planted}"):
        assert_status_current(README, handoffs)


def test_phase27_copy_renamed_to_phase28_fails_against_phase27_status(
    tmp_path: Path,
) -> None:
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    copied = handoffs / "PHASE_27.md"
    shutil.copyfile(HANDOFF_ROOT / "PHASE_27.md", copied)
    copied.rename(handoffs / "PHASE_28.md")
    readme = tmp_path / "README.md"
    readme.write_text(
        "## Next step\n\nPhase 27 truthful current result is "
        "`BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING`.\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match=r"highest handoff is Phase 28"):
        assert_status_current(readme, handoffs)


def test_status_currency_rejects_duplicate_next_step_and_malformed_handoffs(
    tmp_path: Path,
) -> None:
    for duplicate_heading in (
        "## Next step",
        "## Next step ##",
        "   ## Next step",
    ):
        with pytest.raises(AssertionError, match=r"exactly one"):
            next_step_section(
                f"## Next step\n\nPhase 27 is authorized.\n\n{duplicate_heading}\n\nDuplicate.\n"
            )
    with pytest.raises(AssertionError, match=r"exactly one"):
        next_step_section(
            "<!--\n## Next step\n\n"
            "Phase 27 truthful current result is `BLOCKED / RIGHTS_MISSING`.\n-->\n"
        )
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    (handoffs / "PHASE_09.md").write_text("fixture\n", encoding="utf-8")
    (handoffs / "PHASE_10.md").write_text("fixture\n", encoding="utf-8")
    assert highest_handoff_phase(handoffs) == 10
    (handoffs / "PHASE_latest.md").write_text("fixture\n", encoding="utf-8")
    with pytest.raises(AssertionError, match=r"Malformed"):
        highest_handoff_phase(handoffs)


def test_status_parser_ignores_hypothetical_inline_and_fenced_authority() -> None:
    prose = (
        "It would be false to say Phase 28 is accepted.\n"
        "Do not write `Phase 29 is accepted` until approval.\n"
        "```text\n"
        "## Next step\n"
        "Phase 30 is accepted\n"
        "```\n"
        "Phase 31 is authorized.\n"
        "Phase 32 is separately authorized.\n"
        "Phase 33 is accepted if approval arrives.\n"
        "Phase 34 is accepted when evidence is supplied.\n"
        "Phase 35 is accepted only if approval arrives.\n"
        "Phase 36 is accepted subject to later approval.\n"
        "Phase 37 is accepted after approval arrives.\n"
        "Phase 38 is accepted hypothetically for this example.\n"
        "Phase 39 is authorized; its truthful current result is unknown.\n"
        "Phase 40's truthful current result is hypothetical.\n"
        "Phase 41 is formally accepted at commit "
        "`0123456789abcdef0123456789abcdef01234567`, but that claim is false.\n"
        "Phase 42 is formally accepted at commit "
        "`0123456789abcdef0123456789abcdef01234567` only as an example.\n"
        "Phase 43, contingent on approval, truthful current result is "
        "`BLOCKED / RIGHTS_MISSING`.\n"
        "Phase 44, conditional on approval, truthful current result is "
        "`BLOCKED / RIGHTS_MISSING`.\n"
        "Phase 45, assuming approval, truthful current result is "
        "`BLOCKED / RIGHTS_MISSING`.\n"
        "Phase 46 truthful current result is `BLOCKED / EXAMPLE`.\n"
        "Phase 47 truthful current result is `BLOCKED / PLACEHOLDER`.\n"
        "Phase 48 truthful current result is `BLOCKED / SENTINEL`.\n"
        "Phase 49 truthful current result is `BLOCKED / SAMPLE_VALUE`.\n"
        "Phase 50 truthful current result is `BLOCKED / DUMMY_RESULT`.\n"
        "Phase 51 truthful current result is `BLOCKED / NONE`.\n"
        "Phase 52 truthful current result is `BLOCKED / NULL`.\n"
        "Phase 53 truthful current result is `BLOCKED / TODO_RIGHTS`.\n"
        "Phase 54 truthful current result is `BLOCKED / NOT_SET`.\n"
        "Phase 55 truthful current result is `BLOCKED / TO_BE_DETERMINED`.\n"
        "Phase 56 is formally accepted at commit "
        "`0000000000000000000000000000000000000000`, tree "
        "`0000000000000000000000000000000000000000`, "
        "with same-SHA workflow run `0`.\n"
        "Phase 57 truthful current result is `BLOCKED / RIGHTS_MISSING_`.\n"
        "Phase 58 truthful current result is `BLOCKED / RIGHTS__MISSING`.\n"
        "Phase 59 truthful current result is `BLOCKED / A_`.\n"
        "Phase 27 truthful current result is "
        "`BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING`.\n"
    )
    prose = prose.replace("\nPhase", "\n\nPhase")
    assert positive_status_phases(prose) == {27}
    assert positive_status_phases(
        "Phase 26 is formally accepted at commit "
        "`4180ce659aa621d6155cac1118f7011deb92aa9f`, tree "
        "`1c50bd2569dc635c3e5662179ab276f6b971230c`, "
        "with same-SHA Ubuntu workflow run `30050558772`.\n"
    ) == {26}
    assert positive_status_phases(
        "Phase 28 truthful current result is `BLOCKED / RIGHTS_MISSING`.\n"
    ) == {28}
    assert next_step_section(
        "```markdown\n"
        "## Next step\n"
        "```\n\n"
        "## Next step\n\nPhase 27 truthful current result is "
        "`BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING`.\n"
    ).strip() == (
        "Phase 27 truthful current result is "
        "`BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING`."
    )


def test_status_parser_rejects_negative_or_conditional_paragraph_prefixes() -> None:
    for prefix in (
        "It is false that:",
        "If approval arrives:",
        "This hypothetical result says:",
    ):
        assert (
            positive_status_phases(
                f"{prefix}\nPhase 28 truthful current result is `BLOCKED / RIGHTS_MISSING`.\n"
            )
            == set()
        )


def test_governance_files_retain_the_pinned_hard_gate_prefix() -> None:
    gates = canonical_gates()
    assert hashlib.sha256(gates.encode()).hexdigest() == PINNED_GATE_SHA256
    assert GATE_SHA256 == PINNED_GATE_SHA256
    for filename in ("AGENTS.md", "CLAUDE.md"):
        assert normalized(ROOT / filename).startswith(gates + "\n\n")


def test_claude_ends_with_the_verbatim_external_observation_rules() -> None:
    agents = normalized(ROOT / "AGENTS.md")
    claude = normalized(ROOT / "CLAUDE.md")
    expected = h1_section(agents, EXTERNAL_RULES_HEADING)
    assert hashlib.sha256(expected.encode()).hexdigest() == EXTERNAL_RULES_SHA256
    assert_external_rules_are_verbatim(agents, claude)
    accepted_claude = subprocess.run(
        ["git", "show", f"{T010_BASELINE_SHA}:CLAUDE.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    expected_bytes = accepted_claude + expected.encode()
    assert (ROOT / "CLAUDE.md").read_bytes() == expected_bytes


def test_external_rules_mirror_rejects_one_character_drift() -> None:
    agents = normalized(ROOT / "AGENTS.md")
    claude = normalized(ROOT / "CLAUDE.md")
    tampered = claude.replace("Read-only external observation", "Read only external observation", 1)
    with pytest.raises(AssertionError):
        assert_external_rules_are_verbatim(agents, tampered)
