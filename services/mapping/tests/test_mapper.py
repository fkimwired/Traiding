from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any, cast

import fable5_mapping.mapper as mapper_module
import pytest
from fable5_extraction.models import SourceAuthority
from fable5_mapping.mapper import map_idea
from fable5_mapping.models import (
    CanonicalFamily,
    MappingInput,
    MappingReasonCode,
    ResearchVerdict,
)
from fable5_mapping.rules import CURRENT_RULE_SET, MappingRuleSet
from helpers import FIXED_TIME, make_mapping_input, make_source
from pydantic import ValidationError

FIXTURES = Path(__file__).resolve().parents[2] / "extraction" / "tests" / "fixtures"

EXPECTED_FIXTURE_MATRIX = {
    "ranking": (
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        ResearchVerdict.BUILD_RESEARCH,
        (MappingReasonCode.CANON_A_RULE_MATCHED,),
    ),
    "trend": (
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ResearchVerdict.NON_TESTABLE,
        (MappingReasonCode.MISSING_FORECAST_HORIZON,),
    ),
    "social_news": (
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        ResearchVerdict.DEFER,
        (MappingReasonCode.OFFICIAL_CORROBORATION_REQUIRED,),
    ),
    "pairs": (
        CanonicalFamily.D_PAIRS_STATISTICAL_ARBITRAGE,
        ResearchVerdict.DEFER,
        (MappingReasonCode.BORROW_AND_BREAK_REQUIREMENTS,),
    ),
    "order_flow": (
        CanonicalFamily.E_ORDER_BOOK_MICROSTRUCTURE,
        ResearchVerdict.REJECT_PLATFORM,
        (MappingReasonCode.PLATFORM_INFRASTRUCTURE_MISMATCH,),
    ),
    "unusual_options": (
        CanonicalFamily.F_OPTIONS_FLOW_IV_RV_ANALYTICS,
        ResearchVerdict.NON_TESTABLE,
        (MappingReasonCode.MISSING_ACTION_RULE,),
    ),
}


@pytest.mark.parametrize("fixture_name", sorted(EXPECTED_FIXTURE_MATRIX))
def test_six_persisted_phase2_fixtures_follow_fail_closed_precedence(
    fixture_name: str,
) -> None:
    fixture = json.loads((FIXTURES / f"{fixture_name}.json").read_text(encoding="utf-8"))
    mapping_input = make_mapping_input(
        fixture["raw_text"],
        authority=SourceAuthority(fixture["source_authority"]),
    )

    decision = map_idea(mapping_input)

    family, verdict, reasons = EXPECTED_FIXTURE_MATRIX[fixture_name]
    assert decision.canonical_family is family
    assert decision.verdict is verdict
    assert decision.reason_codes == reasons
    assert decision.mapper_rule_set_sha256 == CURRENT_RULE_SET.sha256
    assert decision.matched_rule_ids
    assert decision.source_evidence


def test_structurally_testable_b_and_f_reach_their_family_rules() -> None:
    trend = map_idea(
        make_mapping_input("When the moving average crosses, evaluate the next day trend claim.")
    )
    options = map_idea(
        make_mapping_input(
            "When IV versus RV exceeds a recorded threshold, describe read-only unusual options "
            "analytics over one month using OPRA options quotes."
        )
    )

    assert trend.canonical_family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    assert trend.verdict is ResearchVerdict.BUILD_RESEARCH
    assert options.canonical_family is CanonicalFamily.F_OPTIONS_FLOW_IV_RV_ANALYTICS
    assert options.verdict is ResearchVerdict.DEFER_READ_ONLY
    assert options.reason_codes == (MappingReasonCode.READ_ONLY_ANALYTICS_ONLY,)


def test_ambiguous_family_and_non_testable_precedence_win_over_hft() -> None:
    ambiguous = map_idea(
        make_mapping_input(
            "When moving average trend and order-book scalp conditions occur, evaluate next day "
            "stock claim."
        )
    )
    non_testable_hft = map_idea(
        make_mapping_input("When full-depth order-book state changes, record the scalp claim.")
    )

    assert ambiguous.canonical_family is None
    assert ambiguous.verdict is ResearchVerdict.NON_TESTABLE
    assert ambiguous.reason_codes == (MappingReasonCode.AMBIGUOUS_CANONICAL_FAMILY,)
    assert non_testable_hft.canonical_family is CanonicalFamily.E_ORDER_BOOK_MICROSTRUCTURE
    assert non_testable_hft.verdict is ResearchVerdict.NON_TESTABLE
    assert MappingReasonCode.PLATFORM_INFRASTRUCTURE_MISMATCH not in (non_testable_hft.reason_codes)


def test_verified_official_social_can_build_but_unverified_cannot() -> None:
    official = make_source(
        "Official issuer event evidence.",
        authority=SourceAuthority.OFFICIAL,
    ).model_copy(
        update={
            "authority_verification_method": "synthetic_fixture",
            "source_id": "11000000-0000-0000-0000-000000000099",
            "source_version_id": "22000000-0000-0000-0000-000000000099",
        }
    )
    verified = map_idea(
        make_mapping_input(
            "If Reddit attention rises around an issuer event, news sentiment predicts the next "
            "day for stocks.",
            authority=SourceAuthority.SOCIAL,
            corroborating_versions=[official],
        )
    )

    assert verified.canonical_family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    assert verified.verdict is ResearchVerdict.BUILD_RESEARCH
    assert verified.reason_codes == (MappingReasonCode.CANON_C_RULE_MATCHED,)


def test_mapping_input_rejects_client_verdict_and_raw_text() -> None:
    valid = make_mapping_input(
        "When the moving average crosses, evaluate the next day trend claim."
    ).model_dump(mode="json")
    valid["raw_text"] = "reinterpret me"
    valid["verdict"] = "BUILD_RESEARCH"

    with pytest.raises(ValidationError, match="Extra inputs"):
        MappingInput.model_validate(valid)


def test_rule_set_and_nested_rule_state_are_immutable() -> None:
    rule_set_view = cast(Any, CURRENT_RULE_SET)
    with pytest.raises(FrozenInstanceError):
        rule_set_view.version = "mutated"
    with pytest.raises(TypeError):
        rule_set_view.rule_table[0] = CURRENT_RULE_SET.rule_table[0]
    outcome_view = cast(Any, CURRENT_RULE_SET.rule_table[0].outcome)
    with pytest.raises(FrozenInstanceError):
        outcome_view.verdict = ResearchVerdict.BUILD_RESEARCH

    assert MappingRuleSet.__dataclass_fields__["sha256"].init is False


def test_rule_set_evaluator_identity_matches_exact_mapper_source() -> None:
    mapper_path = Path(mapper_module.__file__ or "")
    source = mapper_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

    assert CURRENT_RULE_SET.evaluator_identity == (f"fable5_mapping.mapper.sha256:{source_sha256}")


def test_changed_rule_outcome_changes_hash_and_executable_result() -> None:
    mapping_input = make_mapping_input(
        "When the moving average crosses, evaluate the next day trend claim."
    )
    changed_rule_table = tuple(
        replace(
            rule,
            outcome=replace(
                rule.outcome,
                verdict=ResearchVerdict.DEFER,
                reason_codes=(MappingReasonCode.BORROW_AND_BREAK_REQUIREMENTS,),
            ),
        )
        if rule.rule_id.value == "P3-CANON-B"
        else rule
        for rule in CURRENT_RULE_SET.rule_table
    )
    changed = replace(
        CURRENT_RULE_SET,
        rule_table=changed_rule_table,
    )

    current = map_idea(mapping_input)
    revised = map_idea(mapping_input, changed)

    assert current.input_sha256 == revised.input_sha256
    assert current.mapper_rule_set_sha256 != revised.mapper_rule_set_sha256
    assert revised.mapper_rule_set_sha256 == changed.sha256
    assert current.verdict is ResearchVerdict.BUILD_RESEARCH
    assert revised.verdict is ResearchVerdict.DEFER
    assert revised.reason_codes == (MappingReasonCode.BORROW_AND_BREAK_REQUIREMENTS,)


def test_changed_family_table_changes_hash_and_executable_family() -> None:
    mapping_input = make_mapping_input(
        "When the moving average crosses, evaluate the next day trend claim."
    )
    family_a = CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    family_b = CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    swapped_family_table = tuple(
        replace(
            rule,
            canonical_family=family_b,
            rule_id=next(
                candidate.rule_id
                for candidate in CURRENT_RULE_SET.family_table
                if candidate.canonical_family is family_b
            ),
        )
        if rule.canonical_family is family_a
        else replace(
            rule,
            canonical_family=family_a,
            rule_id=next(
                candidate.rule_id
                for candidate in CURRENT_RULE_SET.family_table
                if candidate.canonical_family is family_a
            ),
        )
        if rule.canonical_family is family_b
        else rule
        for rule in CURRENT_RULE_SET.family_table
    )
    changed = replace(CURRENT_RULE_SET, family_table=swapped_family_table)

    current = map_idea(mapping_input)
    revised = map_idea(mapping_input, changed)

    assert changed.sha256 != CURRENT_RULE_SET.sha256
    assert current.canonical_family is family_b
    assert revised.canonical_family is family_a
    assert revised.reason_codes == (MappingReasonCode.CANON_A_RULE_MATCHED,)


def test_pure_mapper_has_no_io_model_provider_or_execution_dependency() -> None:
    source = inspect.getsource(__import__("fable5_mapping.mapper", fromlist=["map_idea"]))
    lowered = source.lower()
    for forbidden in (
        "sqlalchemy",
        "requests",
        "urllib",
        "openai",
        "anthropic",
        "provider",
        "broker",
        "submit_order",
        "place_order",
    ):
        assert forbidden not in lowered
    assert FIXED_TIME.tzinfo is not None
