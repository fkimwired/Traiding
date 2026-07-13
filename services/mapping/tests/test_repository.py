from __future__ import annotations

import inspect
from uuid import UUID

import pytest
from fable5_mapping.mapper import map_idea
from fable5_mapping.models import MappingInput, MappingWithRationale, ResearchMapping
from fable5_mapping.rationale import build_mapping_rationale
from fable5_mapping.repository import MappingLineageError, MappingRepository
from helpers import FIXED_TIME, make_mapping_input


def _persisted_bundle(mapping_input: MappingInput) -> MappingWithRationale:
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
    rationale = build_mapping_rationale(
        mapping,
        rationale_id=UUID("66000000-0000-0000-0000-000000000001"),
        created_at_utc=FIXED_TIME,
    )
    return MappingWithRationale(mapping=mapping, rationale=rationale)


def test_existing_mapping_is_revalidated_against_fresh_input_and_decision() -> None:
    mapping_input = make_mapping_input(
        "When the moving average crosses, evaluate the next day trend claim."
    )
    existing = _persisted_bundle(mapping_input)
    decision = map_idea(mapping_input)

    MappingRepository._validate_existing_mapping(existing, mapping_input, decision)

    changed_input = mapping_input.model_copy(update={"card_sha256": "0" * 64})
    with pytest.raises(MappingLineageError, match="card_sha256"):
        MappingRepository._validate_existing_mapping(existing, changed_input, decision)

    changed_decision = decision.model_copy(update={"input_sha256": "f" * 64})
    with pytest.raises(MappingLineageError, match="mapping_input_sha256"):
        MappingRepository._validate_existing_mapping(
            existing,
            mapping_input,
            changed_decision,
        )

    extra_corroboration = existing.mapping.model_copy(
        update={
            "official_corroboration_source_version_ids": (
                UUID("77000000-0000-0000-0000-000000000001"),
            )
        }
    )
    with pytest.raises(
        MappingLineageError,
        match="official_corroboration_source_version_ids",
    ):
        MappingRepository._validate_mapping_parent_lineage(
            extra_corroboration,
            mapping_input,
        )


def test_get_and_list_fail_closed_on_fresh_parent_lineage() -> None:
    for method in (MappingRepository.get_mapping, MappingRepository.list_mappings):
        source = inspect.getsource(method)
        assert "_load_mapping_input" in source
        assert "lock_card=False" in source
        assert "_validate_mapping_parent_lineage" in source
