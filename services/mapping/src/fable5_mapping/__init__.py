"""Deterministic, research-only Phase 3 canon mapping boundary."""

from fable5_mapping.mapper import map_idea
from fable5_mapping.models import (
    CanonicalFamily,
    MappingDecision,
    MappingInput,
    MappingRationale,
    MappingReasonCode,
    MappingRuleId,
    MappingWithRationale,
    ResearchMapping,
    ResearchVerdict,
)
from fable5_mapping.rationale import build_mapping_rationale
from fable5_mapping.rules import CURRENT_RULE_SET, MappingRuleSet

__all__ = [
    "CURRENT_RULE_SET",
    "CanonicalFamily",
    "MappingDecision",
    "MappingInput",
    "MappingRationale",
    "MappingReasonCode",
    "MappingRuleId",
    "MappingRuleSet",
    "MappingWithRationale",
    "ResearchMapping",
    "ResearchVerdict",
    "build_mapping_rationale",
    "map_idea",
]
