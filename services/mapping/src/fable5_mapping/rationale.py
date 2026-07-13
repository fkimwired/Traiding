from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fable5_mapping.models import MappingRationale, ResearchMapping


def render_mapping_rationale(mapping: ResearchMapping) -> str:
    family = "UNRESOLVED" if mapping.canonical_family is None else mapping.canonical_family.value
    reasons = "\n".join(f"- `{reason.value}`" for reason in mapping.reason_codes)
    rules = "\n".join(f"- `{rule.value}`" for rule in mapping.matched_rule_ids)
    evidence = "\n".join(
        f"- `{item.phase2_field}`: state=`{item.state or 'not_applicable'}`, "
        f"value=`{item.value or 'not_applicable'}`, claims="
        f"`{','.join(item.claim_ids) or 'none'}`"
        for item in mapping.source_evidence
    )
    if not evidence:
        evidence = "- No claim-level evidence exists for the missing field."
    return (
        "# Deterministic canon mapping rationale\n\n"
        "> Research classification only. This is not investment advice, a recommendation, a "
        "trading signal, an instruction, a position size, a performance claim, an approval, or "
        "paper-trading eligibility.\n\n"
        "## Deterministic result\n\n"
        f"- Canonical family: `{family}`\n"
        f"- Research verdict: `{mapping.verdict.value}`\n"
        f"- Mapping version: `{mapping.mapping_version}`\n"
        f"- Rule set: `{mapping.mapper_rule_set_version}` "
        f"(`{mapping.mapper_rule_set_sha256}`)\n\n"
        "`BUILD_RESEARCH` authorizes only a later research specification. It does not mean "
        "profitable, approved, recommended, or paper-eligible.\n\n"
        "## Ordered reason codes\n\n"
        f"{reasons}\n\n"
        "## Matched rule IDs\n\n"
        f"{rules}\n\n"
        "## Persisted source evidence\n\n"
        f"{evidence}\n\n"
        "## Immutable lineage\n\n"
        f"- Card: `{mapping.card_id}` (`{mapping.card_sha256}`)\n"
        f"- Extraction request: `{mapping.extraction_request_id}` "
        f"(`{mapping.extraction_request_fingerprint}`)\n"
        f"- Source: `{mapping.source_id}`\n"
        f"- Source version: `{mapping.source_version_id}` (version {mapping.source_version}, "
        f"content `{mapping.source_content_sha256}`)\n"
        f"- Extraction schema: `{mapping.extraction_schema_version}`\n"
        f"- Extraction configuration: `{mapping.extraction_config_sha256}`\n"
        f"- Mapping input: `{mapping.mapping_input_sha256}`\n\n"
        "No provider, feature, model, backtest, risk, portfolio, broker, paper-order, or live "
        "capability is created by this artifact.\n"
    )


def build_mapping_rationale(
    mapping: ResearchMapping,
    *,
    rationale_id: UUID | None = None,
    created_at_utc: datetime | None = None,
) -> MappingRationale:
    markdown = render_mapping_rationale(mapping)
    return MappingRationale(
        rationale_id=rationale_id or uuid4(),
        mapping_id=mapping.mapping_id,
        template_version=mapping.rationale_template_version,
        markdown=markdown,
        content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        created_at_utc=created_at_utc or datetime.now(UTC),
    )


__all__ = ["build_mapping_rationale", "render_mapping_rationale"]
