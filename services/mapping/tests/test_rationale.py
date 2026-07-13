from __future__ import annotations

from uuid import UUID

from fable5_mapping.mapper import map_idea
from fable5_mapping.models import ResearchMapping
from fable5_mapping.rationale import build_mapping_rationale
from helpers import FIXED_TIME, make_mapping_input


def test_rationale_is_deterministic_traceable_and_research_only() -> None:
    mapping_input = make_mapping_input(
        "When the moving average crosses, evaluate the next day trend claim."
    )
    decision = map_idea(mapping_input)
    mapping = ResearchMapping(
        mapping_id=UUID("55000000-0000-0000-0000-000000000001"),
        mapping_version=1,
        card_id=mapping_input.card_id,
        card_sha256=mapping_input.card_sha256,
        mapping_input_sha256=decision.input_sha256,
        extraction_request_id=mapping_input.extraction_request_id,
        extraction_request_fingerprint=mapping_input.extraction_request_fingerprint,
        source_id=mapping_input.source_id,
        source_version_id=mapping_input.source_version_id,
        source_version=mapping_input.source_version,
        source_content_sha256=mapping_input.source_content_sha256,
        official_corroboration_source_version_ids=(
            mapping_input.official_corroboration_source_version_ids
        ),
        extractor_kind=mapping_input.extractor_kind,
        extractor_id=mapping_input.extractor_id,
        extractor_version=mapping_input.extractor_version,
        extraction_model_id=mapping_input.extraction_model_id,
        extraction_model_revision=mapping_input.extraction_model_revision,
        extraction_prompt_version=mapping_input.extraction_prompt_version,
        extraction_prompt_sha256=mapping_input.extraction_prompt_sha256,
        extraction_schema_version=mapping_input.extraction_schema_version,
        extraction_config_sha256=mapping_input.extraction_config_sha256,
        canonical_family=decision.canonical_family,
        verdict=decision.verdict,
        matched_rule_ids=decision.matched_rule_ids,
        reason_codes=decision.reason_codes,
        mapper_rule_set_version=decision.mapper_rule_set_version,
        mapper_rule_set_sha256=decision.mapper_rule_set_sha256,
        source_evidence=decision.source_evidence,
        rationale_template_version=decision.rationale_template_version,
        created_at_utc=FIXED_TIME,
    )

    first = build_mapping_rationale(
        mapping,
        rationale_id=UUID("66000000-0000-0000-0000-000000000001"),
        created_at_utc=FIXED_TIME,
    )
    second = build_mapping_rationale(
        mapping,
        rationale_id=first.rationale_id,
        created_at_utc=FIXED_TIME,
    )

    assert first == second
    assert str(mapping.card_id) in first.markdown
    assert mapping.mapper_rule_set_sha256 in first.markdown
    assert "not investment advice" in first.markdown
    assert "authorizes only a later research specification" in first.markdown
    assert "position size" in first.markdown
    assert "paper-trading eligibility" in first.markdown
