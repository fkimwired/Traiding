from __future__ import annotations

from typing import assert_never

from fable5_extraction.models import (
    ContributionStatus,
    EvidenceState,
    ExecutionStyle,
    ForecastHorizon,
    InfraRisk,
    RequiredData,
    TestabilityStatus,
)

from fable5_mapping.models import (
    CanonicalFamily,
    MappingDecision,
    MappingEvidenceReference,
    MappingInput,
    MappingReasonCode,
    MappingRuleId,
    ResearchVerdict,
)
from fable5_mapping.rules import (
    CURRENT_RULE_SET,
    MappingRule,
    MappingRuleSet,
    NonTestableReasonPolicy,
    RuleEvaluatorId,
    canonical_sha256,
)


def _family(
    mapping_input: MappingInput,
    rule_set: MappingRuleSet,
) -> CanonicalFamily | None:
    evidence = mapping_input.signal_family
    if evidence.state is not EvidenceState.SOURCE_SUPPORTED or evidence.value is None:
        return None
    for rule in rule_set.family_table:
        if rule.phase2_signal_family is evidence.value:
            return rule.canonical_family
    raise ValueError(f"unmapped Phase 2 signal family: {evidence.value.value}")


def _family_rule_id(
    rule_set: MappingRuleSet,
    family: CanonicalFamily,
) -> MappingRuleId:
    for rule in rule_set.family_table:
        if rule.canonical_family is family:
            return rule.rule_id
    raise ValueError(f"unmapped canonical family: {family.value}")


def _reference(
    phase2_field: str,
    *,
    state: EvidenceState | None = None,
    value: str | None = None,
    claim_ids: tuple[str, ...] = (),
) -> MappingEvidenceReference:
    return MappingEvidenceReference.model_validate(
        {
            "phase2_field": phase2_field,
            "state": state,
            "value": value,
            "claim_ids": claim_ids,
        }
    )


def _family_reference(mapping_input: MappingInput) -> MappingEvidenceReference:
    evidence = mapping_input.signal_family
    return _reference(
        "signal_family",
        state=evidence.state,
        value=None if evidence.value is None else evidence.value.value,
        claim_ids=evidence.claim_ids,
    )


def _dedupe_evidence(
    references: list[MappingEvidenceReference],
) -> tuple[MappingEvidenceReference, ...]:
    result: list[MappingEvidenceReference] = []
    seen: set[tuple[object, ...]] = set()
    for reference in references:
        key = (
            reference.phase2_field,
            reference.state,
            reference.value,
            reference.claim_ids,
        )
        if key not in seen:
            seen.add(key)
            result.append(reference)
    return tuple(result)


def _decision(
    mapping_input: MappingInput,
    rule_set: MappingRuleSet,
    *,
    family: CanonicalFamily | None,
    verdict: ResearchVerdict,
    rule_ids: tuple[MappingRuleId, ...],
    reasons: tuple[MappingReasonCode, ...],
    evidence: list[MappingEvidenceReference],
) -> MappingDecision:
    input_sha256 = canonical_sha256(mapping_input.model_dump(mode="json"))
    return MappingDecision(
        canonical_family=family,
        verdict=verdict,
        matched_rule_ids=rule_ids,
        reason_codes=reasons,
        mapper_rule_set_version=rule_set.version,
        mapper_rule_set_sha256=rule_set.sha256,
        source_evidence=_dedupe_evidence(evidence),
        rationale_template_version=rule_set.rationale_template_version,
        input_sha256=input_sha256,
    )


def _platform_mismatch_evidence(
    mapping_input: MappingInput,
    family: CanonicalFamily | None,
) -> list[MappingEvidenceReference]:
    references: list[MappingEvidenceReference] = []
    if family is CanonicalFamily.E_ORDER_BOOK_MICROSTRUCTURE:
        references.append(_family_reference(mapping_input))
    if (
        mapping_input.execution_style.state is EvidenceState.SOURCE_SUPPORTED
        and mapping_input.execution_style.value is ExecutionStyle.HIGH_FREQUENCY_CLAIM
    ):
        references.append(
            _reference(
                "execution_style",
                state=mapping_input.execution_style.state,
                value=mapping_input.execution_style.value.value,
                claim_ids=mapping_input.execution_style.claim_ids,
            )
        )
    if (
        mapping_input.forecast_horizon.state is EvidenceState.SOURCE_SUPPORTED
        and mapping_input.forecast_horizon.value is ForecastHorizon.SUB_MINUTE
    ):
        references.append(
            _reference(
                "forecast_horizon",
                state=mapping_input.forecast_horizon.state,
                value=mapping_input.forecast_horizon.value.value,
                claim_ids=mapping_input.forecast_horizon.claim_ids,
            )
        )
    if RequiredData.FULL_DEPTH_ORDER_BOOK in mapping_input.required_data.values:
        references.append(
            _reference(
                "required_data",
                state=mapping_input.required_data.state,
                value=RequiredData.FULL_DEPTH_ORDER_BOOK.value,
                claim_ids=mapping_input.required_data.claim_ids,
            )
        )
    if mapping_input.infra_risk is InfraRisk.HIGH:
        references.append(_reference("infra_risk", value=InfraRisk.HIGH.value))
    return references


def _evaluate_rule(
    rule: MappingRule,
    mapping_input: MappingInput,
    family: CanonicalFamily | None,
) -> list[MappingEvidenceReference] | None:
    if rule.evaluator_id is RuleEvaluatorId.NON_TESTABLE_OR_UNRESOLVED_FAMILY:
        if mapping_input.testability_status is TestabilityStatus.NON_TESTABLE or family is None:
            return [
                _reference("testability", value=reason.value)
                for reason in mapping_input.testability_reason_codes
            ]
        return None

    if rule.evaluator_id is RuleEvaluatorId.PLATFORM_INFRASTRUCTURE_MISMATCH:
        evidence = _platform_mismatch_evidence(mapping_input, family)
        return evidence or None

    if rule.evaluator_id is RuleEvaluatorId.BLOCKED_OFFICIAL_CORROBORATION:
        if (
            family is rule.canonical_family_condition
            and mapping_input.contribution_status
            is ContributionStatus.BLOCKED_OFFICIAL_CORROBORATION_REQUIRED
        ):
            return [
                _reference(
                    "contribution_status",
                    value=mapping_input.contribution_status.value,
                ),
                _reference(
                    "corroboration_status",
                    value=mapping_input.corroboration_status.value,
                ),
            ]
        return None

    if rule.evaluator_id is RuleEvaluatorId.CANONICAL_FAMILY_EQUALS:
        return [] if family is rule.canonical_family_condition else None

    assert_never(rule.evaluator_id)


def _non_testable_reasons(
    mapping_input: MappingInput,
    family: CanonicalFamily | None,
    rule_set: MappingRuleSet,
    policy: NonTestableReasonPolicy,
) -> tuple[MappingReasonCode, ...]:
    reasons: list[MappingReasonCode] = []
    if policy.include_phase2_reasons:
        reasons.extend(
            rule.mapping_reason
            for rule in rule_set.phase2_reason_order
            if rule.phase2_reason in mapping_input.testability_reason_codes
        )
    if mapping_input.signal_family.state is EvidenceState.AMBIGUOUS:
        reasons.append(policy.ambiguous_family_reason)
    elif family is None:
        reasons.append(policy.missing_family_reason)
    if not reasons:
        reasons.append(policy.empty_reason_fallback)
    return tuple(reasons)


def _rule_reasons(
    rule: MappingRule,
    mapping_input: MappingInput,
    family: CanonicalFamily | None,
    rule_set: MappingRuleSet,
) -> tuple[MappingReasonCode, ...]:
    policy = rule.outcome.non_testable_reason_policy
    if policy is None:
        return rule.outcome.reason_codes
    return _non_testable_reasons(mapping_input, family, rule_set, policy)


def map_idea(
    mapping_input: MappingInput,
    rule_set: MappingRuleSet = CURRENT_RULE_SET,
) -> MappingDecision:
    """Map persisted Phase 2 fields through the immutable deterministic rule table."""

    family = _family(mapping_input, rule_set)
    base_evidence = [_family_reference(mapping_input)]

    for rule in rule_set.rule_table:
        matched_evidence = _evaluate_rule(rule, mapping_input, family)
        if matched_evidence is None:
            continue

        outcome_family = rule.outcome.canonical_family_override or family
        matched_rule_ids = [rule.rule_id]
        if outcome_family is not None:
            family_rule_id = _family_rule_id(rule_set, outcome_family)
            if family_rule_id not in matched_rule_ids:
                matched_rule_ids.append(family_rule_id)
        return _decision(
            mapping_input,
            rule_set,
            family=outcome_family,
            verdict=rule.outcome.verdict,
            rule_ids=tuple(matched_rule_ids),
            reasons=_rule_reasons(rule, mapping_input, family, rule_set),
            evidence=[*base_evidence, *matched_evidence],
        )

    raise ValueError("persisted Phase 2 fields did not match the closed Phase 3 rule table")


__all__ = ["map_idea"]
