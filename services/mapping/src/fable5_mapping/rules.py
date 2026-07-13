from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

from fable5_extraction.models import SignalFamily, TestabilityReason

from fable5_mapping.models import (
    CanonicalFamily,
    MappingReasonCode,
    MappingRuleId,
    ResearchVerdict,
)


def canonical_sha256(payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


class RuleEvaluatorId(StrEnum):
    """Stable identities for the closed, deterministic predicate implementations."""

    NON_TESTABLE_OR_UNRESOLVED_FAMILY = "non_testable_or_unresolved_family_v1"
    PLATFORM_INFRASTRUCTURE_MISMATCH = "platform_infrastructure_mismatch_v1"
    BLOCKED_OFFICIAL_CORROBORATION = "blocked_official_corroboration_v1"
    CANONICAL_FAMILY_EQUALS = "canonical_family_equals_v1"


@dataclass(frozen=True, slots=True)
class FamilyRule:
    phase2_signal_family: SignalFamily
    canonical_family: CanonicalFamily
    rule_id: MappingRuleId

    def hash_payload(self) -> dict[str, str]:
        return {
            "phase2_signal_family": self.phase2_signal_family.value,
            "canonical_family": self.canonical_family.value,
            "rule_id": self.rule_id.value,
        }


@dataclass(frozen=True, slots=True)
class Phase2ReasonRule:
    phase2_reason: TestabilityReason
    mapping_reason: MappingReasonCode

    def hash_payload(self) -> dict[str, str]:
        return {
            "phase2_reason": self.phase2_reason.value,
            "mapping_reason": self.mapping_reason.value,
        }


@dataclass(frozen=True, slots=True)
class NonTestableReasonPolicy:
    include_phase2_reasons: bool
    missing_family_reason: MappingReasonCode
    ambiguous_family_reason: MappingReasonCode
    empty_reason_fallback: MappingReasonCode

    def hash_payload(self) -> dict[str, object]:
        return {
            "include_phase2_reasons": self.include_phase2_reasons,
            "missing_family_reason": self.missing_family_reason.value,
            "ambiguous_family_reason": self.ambiguous_family_reason.value,
            "empty_reason_fallback": self.empty_reason_fallback.value,
        }


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    verdict: ResearchVerdict
    reason_codes: tuple[MappingReasonCode, ...]
    canonical_family_override: CanonicalFamily | None = None
    non_testable_reason_policy: NonTestableReasonPolicy | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.non_testable_reason_policy is None and not self.reason_codes:
            raise ValueError("a static rule outcome requires at least one reason code")
        if (
            self.non_testable_reason_policy is not None
            and self.verdict is not ResearchVerdict.NON_TESTABLE
        ):
            raise ValueError("only NON_TESTABLE outcomes may use a dynamic reason policy")

    def hash_payload(self) -> dict[str, object]:
        return {
            "verdict": self.verdict.value,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "canonical_family_override": (
                None
                if self.canonical_family_override is None
                else self.canonical_family_override.value
            ),
            "non_testable_reason_policy": (
                None
                if self.non_testable_reason_policy is None
                else self.non_testable_reason_policy.hash_payload()
            ),
        }


@dataclass(frozen=True, slots=True)
class MappingRule:
    rule_id: MappingRuleId
    evaluator_id: RuleEvaluatorId
    outcome: RuleOutcome
    canonical_family_condition: CanonicalFamily | None = None

    def __post_init__(self) -> None:
        needs_family = self.evaluator_id in {
            RuleEvaluatorId.BLOCKED_OFFICIAL_CORROBORATION,
            RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        }
        if needs_family != (self.canonical_family_condition is not None):
            raise ValueError(f"{self.evaluator_id.value} family-condition configuration is invalid")
        if (self.evaluator_id is RuleEvaluatorId.NON_TESTABLE_OR_UNRESOLVED_FAMILY) != (
            self.outcome.non_testable_reason_policy is not None
        ):
            raise ValueError("the non-testable evaluator requires its dynamic reason policy")

    def hash_payload(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id.value,
            "evaluator_id": self.evaluator_id.value,
            "canonical_family_condition": (
                None
                if self.canonical_family_condition is None
                else self.canonical_family_condition.value
            ),
            "outcome": self.outcome.hash_payload(),
        }


@dataclass(frozen=True, slots=True)
class MappingRuleSet:
    version: str
    rationale_template_version: str
    evaluator_identity: str
    family_table: tuple[FamilyRule, ...]
    rule_table: tuple[MappingRule, ...]
    phase2_reason_order: tuple[Phase2ReasonRule, ...]
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        # Normalize every collection to a tuple before validating or hashing. This keeps
        # callers from retaining a mutable list that can alter an initialized rule set.
        object.__setattr__(self, "family_table", tuple(self.family_table))
        object.__setattr__(self, "rule_table", tuple(self.rule_table))
        object.__setattr__(self, "phase2_reason_order", tuple(self.phase2_reason_order))
        if not self.version or not self.rationale_template_version or not self.evaluator_identity:
            raise ValueError("rule-set identities cannot be blank")
        if not self.family_table or not self.rule_table or not self.phase2_reason_order:
            raise ValueError("rule-set tables cannot be empty")

        phase2_families = [rule.phase2_signal_family for rule in self.family_table]
        canonical_families = [rule.canonical_family for rule in self.family_table]
        family_rule_ids = [rule.rule_id for rule in self.family_table]
        if len(phase2_families) != len(set(phase2_families)):
            raise ValueError("Phase 2 family mappings must be unique")
        if len(canonical_families) != len(set(canonical_families)):
            raise ValueError("canonical family mappings must be unique")
        if len(family_rule_ids) != len(set(family_rule_ids)):
            raise ValueError("canonical family rule IDs must be unique")

        mapping_rule_ids = [rule.rule_id for rule in self.rule_table]
        if len(mapping_rule_ids) != len(set(mapping_rule_ids)):
            raise ValueError("mapping rule IDs must be unique")
        known_families = set(canonical_families)
        for rule in self.rule_table:
            referenced_families = {
                rule.canonical_family_condition,
                rule.outcome.canonical_family_override,
            } - {None}
            if not referenced_families <= known_families:
                raise ValueError("mapping rules may only reference canonical family-table values")

        phase2_reasons = [rule.phase2_reason for rule in self.phase2_reason_order]
        mapping_reasons = [rule.mapping_reason for rule in self.phase2_reason_order]
        if len(phase2_reasons) != len(set(phase2_reasons)):
            raise ValueError("Phase 2 reason-order entries must be unique")
        if len(mapping_reasons) != len(set(mapping_reasons)):
            raise ValueError("mapped reason-order entries must be unique")

        object.__setattr__(self, "sha256", canonical_sha256(self._hash_payload()))

    def _hash_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "rationale_template_version": self.rationale_template_version,
            "evaluator_identity": self.evaluator_identity,
            "family_table": [rule.hash_payload() for rule in self.family_table],
            "rule_table": [rule.hash_payload() for rule in self.rule_table],
            "phase2_reason_order": [rule.hash_payload() for rule in self.phase2_reason_order],
        }


_FAMILY_TABLE = (
    FamilyRule(
        SignalFamily.CROSS_SECTIONAL_RANKING_CLAIM,
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        MappingRuleId.CANON_A,
    ),
    FamilyRule(
        SignalFamily.TREND_OR_PATTERN_CLAIM,
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        MappingRuleId.CANON_B,
    ),
    FamilyRule(
        SignalFamily.SOCIAL_OR_NEWS_CLAIM,
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        MappingRuleId.CANON_C,
    ),
    FamilyRule(
        SignalFamily.PAIRS_OR_DIVERGENCE_CLAIM,
        CanonicalFamily.D_PAIRS_STATISTICAL_ARBITRAGE,
        MappingRuleId.CANON_D,
    ),
    FamilyRule(
        SignalFamily.ORDER_FLOW_CLAIM,
        CanonicalFamily.E_ORDER_BOOK_MICROSTRUCTURE,
        MappingRuleId.CANON_E,
    ),
    FamilyRule(
        SignalFamily.UNUSUAL_OPTIONS_CLAIM,
        CanonicalFamily.F_OPTIONS_FLOW_IV_RV_ANALYTICS,
        MappingRuleId.CANON_F,
    ),
)

_NON_TESTABLE_POLICY = NonTestableReasonPolicy(
    include_phase2_reasons=True,
    missing_family_reason=MappingReasonCode.MISSING_CANONICAL_FAMILY,
    ambiguous_family_reason=MappingReasonCode.AMBIGUOUS_CANONICAL_FAMILY,
    empty_reason_fallback=MappingReasonCode.MISSING_CANONICAL_FAMILY,
)

_RULE_TABLE = (
    MappingRule(
        rule_id=MappingRuleId.NON_TESTABLE_PRECEDENCE,
        evaluator_id=RuleEvaluatorId.NON_TESTABLE_OR_UNRESOLVED_FAMILY,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.NON_TESTABLE,
            reason_codes=(),
            non_testable_reason_policy=_NON_TESTABLE_POLICY,
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.PLATFORM_MISMATCH_PRECEDENCE,
        evaluator_id=RuleEvaluatorId.PLATFORM_INFRASTRUCTURE_MISMATCH,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.REJECT_PLATFORM,
            reason_codes=(MappingReasonCode.PLATFORM_INFRASTRUCTURE_MISMATCH,),
            canonical_family_override=CanonicalFamily.E_ORDER_BOOK_MICROSTRUCTURE,
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.SOCIAL_CORROBORATION_PRECEDENCE,
        evaluator_id=RuleEvaluatorId.BLOCKED_OFFICIAL_CORROBORATION,
        canonical_family_condition=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.DEFER,
            reason_codes=(MappingReasonCode.OFFICIAL_CORROBORATION_REQUIRED,),
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.PAIRS_REQUIREMENTS_PRECEDENCE,
        evaluator_id=RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        canonical_family_condition=CanonicalFamily.D_PAIRS_STATISTICAL_ARBITRAGE,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.DEFER,
            reason_codes=(MappingReasonCode.BORROW_AND_BREAK_REQUIREMENTS,),
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.OPTIONS_READ_ONLY_PRECEDENCE,
        evaluator_id=RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        canonical_family_condition=CanonicalFamily.F_OPTIONS_FLOW_IV_RV_ANALYTICS,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.DEFER_READ_ONLY,
            reason_codes=(MappingReasonCode.READ_ONLY_ANALYTICS_ONLY,),
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.CANON_A,
        evaluator_id=RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        canonical_family_condition=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.BUILD_RESEARCH,
            reason_codes=(MappingReasonCode.CANON_A_RULE_MATCHED,),
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.CANON_B,
        evaluator_id=RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        canonical_family_condition=CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.BUILD_RESEARCH,
            reason_codes=(MappingReasonCode.CANON_B_RULE_MATCHED,),
        ),
    ),
    MappingRule(
        rule_id=MappingRuleId.CANON_C,
        evaluator_id=RuleEvaluatorId.CANONICAL_FAMILY_EQUALS,
        canonical_family_condition=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        outcome=RuleOutcome(
            verdict=ResearchVerdict.BUILD_RESEARCH,
            reason_codes=(MappingReasonCode.CANON_C_RULE_MATCHED,),
        ),
    ),
)

_PHASE2_REASON_ORDER = (
    Phase2ReasonRule(
        TestabilityReason.MISSING_RAW_TEXT,
        MappingReasonCode.MISSING_RAW_TEXT,
    ),
    Phase2ReasonRule(
        TestabilityReason.MISSING_ACTION_RULE,
        MappingReasonCode.MISSING_ACTION_RULE,
    ),
    Phase2ReasonRule(
        TestabilityReason.AMBIGUOUS_ACTION_RULE,
        MappingReasonCode.AMBIGUOUS_ACTION_RULE,
    ),
    Phase2ReasonRule(
        TestabilityReason.MISSING_FORECAST_HORIZON,
        MappingReasonCode.MISSING_FORECAST_HORIZON,
    ),
    Phase2ReasonRule(
        TestabilityReason.AMBIGUOUS_FORECAST_HORIZON,
        MappingReasonCode.AMBIGUOUS_FORECAST_HORIZON,
    ),
)

CURRENT_RULE_SET = MappingRuleSet(
    version="phase3-canon-mapping-v1",
    rationale_template_version="phase3-mapping-rationale-v1",
    evaluator_identity=(
        "fable5_mapping.mapper.sha256:"
        "63e34130c4bf8d9ca0a4a82db6c37e0034282646dcfc66781675621ee69b2e18"
    ),
    family_table=_FAMILY_TABLE,
    rule_table=_RULE_TABLE,
    phase2_reason_order=_PHASE2_REASON_ORDER,
)

__all__ = [
    "CURRENT_RULE_SET",
    "FamilyRule",
    "MappingRule",
    "MappingRuleSet",
    "NonTestableReasonPolicy",
    "Phase2ReasonRule",
    "RuleEvaluatorId",
    "RuleOutcome",
    "canonical_sha256",
]
