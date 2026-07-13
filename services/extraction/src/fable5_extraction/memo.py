from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fable5_extraction.models import ResearchMemo, TradingIdeaCard


def render_research_memo(card: TradingIdeaCard) -> str:
    evidence = "\n".join(
        f"- `{claim.claim_id}`: bytes {claim.span.start_byte}:{claim.span.end_byte}, "
        f"SHA-256 `{claim.span.text_sha256}`"
        for claim in card.quoted_claims
    )
    if not evidence:
        evidence = "- No text evidence was available."
    blockers = "\n".join(f"- `{flag.value}`" for flag in card.ambiguity_flags)
    if not blockers:
        blockers = "- None recorded at intake."
    synthetic = (
        "This memo uses a clearly labeled synthetic fixture."
        if card.synthetic_fixture
        else "This memo records supplied provenance; it does not authenticate an external URL."
    )
    return (
        "# TradingIdeaCard research memo\n\n"
        "> Extraction-only research artifact. It is not investment advice, a trading signal, "
        "a recommendation, or evidence of performance. No order or execution path exists.\n\n"
        f"{synthetic}\n\n"
        "## Lineage\n\n"
        f"- Source: `{card.source_id}`\n"
        f"- Source version: `{card.source_version_id}` (version {card.source_version})\n"
        f"- Extraction request: `{card.extraction_request_id}`\n"
        f"- Extraction schema: `{card.extraction_schema_version}`\n"
        f"- Extractor: `{card.extractor_id}` version `{card.extractor_version}`\n"
        f"- Model: `{card.extraction_model_id or 'not_applicable'}`\n"
        f"- Prompt: `{card.extraction_prompt_version or 'not_applicable'}`\n\n"
        "## Source-evidence references\n\n"
        f"{evidence}\n\n"
        "The exact quotations remain in the immutable card/source response. They are not repeated "
        "here as instructions.\n\n"
        "## Intake assessment\n\n"
        f"- Neutral claim summary: {card.paraphrased_claim or 'Not stated.'}\n"
        f"- Testability: `{card.testability_status.value}`\n"
        f"- Evidence-completeness score: `{card.testability_score:.1f}` "
        f"(`{card.testability_score_method}`)\n"
        f"- Infrastructure risk: `{card.infra_risk.value}`\n"
        f"- Corroboration: `{card.corroboration_status.value}`\n"
        f"- Social contribution gate: `{card.contribution_status.value}`\n"
        "- Research priority: `not_defined_in_phase_2`\n\n"
        "## Ambiguity and blockers\n\n"
        f"{blockers}\n\n"
        "## Phase boundary\n\n"
        "This artifact stops at source extraction. It contains no deterministic family verdict, "
        "backtest, performance result, risk approval, paper instruction, or live capability.\n"
    )


def build_research_memo(
    card: TradingIdeaCard,
    *,
    memo_id: UUID | None = None,
    created_at_utc: datetime | None = None,
) -> ResearchMemo:
    markdown = render_research_memo(card)
    return ResearchMemo(
        memo_id=memo_id or uuid4(),
        card_id=card.card_id,
        markdown=markdown,
        content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        created_at_utc=created_at_utc or datetime.now(UTC),
    )
