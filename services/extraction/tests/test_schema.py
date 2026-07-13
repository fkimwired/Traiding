from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fable5_extraction.extractor import (
    DraftAssetClassEvidence,
    DraftExecutionStyleEvidence,
    DraftForecastHorizonEvidence,
    DraftRequiredDataEvidence,
    DraftRiskAssumptionsEvidence,
    DraftSignalFamilyEvidence,
    default_extraction_profile,
)
from fable5_extraction.models import (
    ActionRuleEvidence,
    AssetClassEvidence,
    EvidenceState,
    ExecutionStyleEvidence,
    ExtractionProfile,
    ExtractorKind,
    ForecastHorizonEvidence,
    RequiredDataEvidence,
    RiskAssumptionsEvidence,
    SignalFamilyEvidence,
    SourceAuthority,
    SourceIntakeRequest,
    SourceType,
    TradingIdeaCard,
)
from pydantic import BaseModel, ValidationError


def test_unknowns_are_explicit_and_extra_instruction_fields_are_forbidden() -> None:
    unknown = AssetClassEvidence(state=EvidenceState.NOT_STATED, value=None, claim_ids=[])
    assert unknown.model_dump(mode="json") == {
        "state": "not_stated",
        "value": None,
        "claim_ids": [],
    }

    with pytest.raises(ValidationError):
        AssetClassEvidence(
            state=EvidenceState.SOURCE_SUPPORTED,
            value="unknown",
            claim_ids=["segment-001"],
        )
    with pytest.raises(ValidationError):
        AssetClassEvidence(state=EvidenceState.NOT_STATED, value="equity", claim_ids=[])
    with pytest.raises(ValidationError):
        ActionRuleEvidence.model_validate(
            {
                "state": "source_supported",
                "claim_ids": ["segment-001"],
                "text": "impermissible free-form rule",
            }
        )


@pytest.mark.parametrize(
    ("evidence_type", "field", "wrong_value"),
    [
        (AssetClassEvidence, "value", "next_day"),
        (ForecastHorizonEvidence, "value", "equity"),
        (SignalFamilyEvidence, "value", "high_frequency_claim"),
        (ExecutionStyleEvidence, "value", "trend_or_pattern_claim"),
        (RequiredDataEvidence, "values", ["liquidity"]),
        (RiskAssumptionsEvidence, "values", ["ohlcv"]),
    ],
)
def test_public_evidence_rejects_cross_field_vocabulary(
    evidence_type: type[BaseModel], field: str, wrong_value: object
) -> None:
    payload = {
        "state": "source_supported",
        field: wrong_value,
        "claim_ids": ["segment-001"],
    }
    with pytest.raises(ValidationError):
        evidence_type.model_validate(payload)


@pytest.mark.parametrize(
    ("evidence_type", "field", "wrong_value"),
    [
        (DraftAssetClassEvidence, "value", "next_day"),
        (DraftForecastHorizonEvidence, "value", "equity"),
        (DraftSignalFamilyEvidence, "value", "high_frequency_claim"),
        (DraftExecutionStyleEvidence, "value", "trend_or_pattern_claim"),
        (DraftRequiredDataEvidence, "values", ["liquidity"]),
        (DraftRiskAssumptionsEvidence, "values", ["ohlcv"]),
    ],
)
def test_untrusted_draft_rejects_cross_field_vocabulary(
    evidence_type: type[BaseModel], field: str, wrong_value: object
) -> None:
    payload = {
        "state": "source_supported",
        field: wrong_value,
        "segment_ids": ["segment-001"],
    }
    with pytest.raises(ValidationError):
        evidence_type.model_validate(payload)


def test_llm_provenance_is_conditional_and_mock_fields_are_null() -> None:
    mock = default_extraction_profile()
    dumped = mock.model_dump(mode="json")
    assert dumped["extraction_model_id"] is None
    assert dumped["extraction_prompt_version"] is None

    with pytest.raises(ValidationError):
        ExtractionProfile(
            extractor_kind=ExtractorKind.LLM,
            extractor_id="review-only",
            extractor_version="1",
            extraction_config_sha256="0" * 64,
        )
    with pytest.raises(ValidationError):
        ExtractionProfile(
            extractor_kind=ExtractorKind.DETERMINISTIC_MOCK,
            extractor_id="mock",
            extractor_version="1",
            extraction_model_id="fabricated-model",
            extraction_config_sha256="0" * 64,
        )


def test_source_intake_requires_content_or_provenance_and_aware_time() -> None:
    with pytest.raises(ValidationError):
        SourceIntakeRequest(source_type=SourceType.MANUAL_NOTES)
    with pytest.raises(ValidationError):
        SourceIntakeRequest.model_validate(
            {
                "source_type": "manual_notes",
                "raw_text": "text",
                "supplied_at_utc": "2026-07-13T20:00:00Z",
            }
        )

    for raw_text in ("", " ", "\t\r\n", "\u2003"):
        with pytest.raises(ValidationError, match="non-whitespace"):
            SourceIntakeRequest(source_type=SourceType.MANUAL_NOTES, raw_text=raw_text)

    request = SourceIntakeRequest(
        source_type=SourceType.URL_PROVENANCE,
        source_url="https://example.invalid/source",
    )
    assert request.raw_text is None
    with pytest.raises(ValidationError, match="must omit raw_text"):
        SourceIntakeRequest.model_validate(
            {
                "source_type": "url_provenance",
                "source_url": "https://example.invalid/source",
                "raw_text": None,
            }
        )
    with pytest.raises(ValidationError):
        SourceIntakeRequest(
            source_type=SourceType.URL_PROVENANCE,
            source_url="file:///local/not-allowed",
        )
    with pytest.raises(ValidationError):
        SourceIntakeRequest.model_validate(
            {
                "source_type": "synthetic_fixture",
                "source_authority": "official",
                "raw_text": "fixture",
                "authority_verification_method": "llm_asserted",
            }
        )

    offset = timezone(timedelta(hours=5))
    normalized = SourceIntakeRequest(
        source_type=SourceType.MANUAL_NOTES,
        raw_text="text",
        retrieved_at_utc=datetime(2026, 7, 14, 1, 0, tzinfo=offset),
    )
    assert normalized.retrieved_at_utc == datetime(2026, 7, 13, 20, 0, tzinfo=UTC)


def test_public_card_serializes_all_required_unknown_fields(build_fixture_card: object) -> None:
    card = build_fixture_card(  # type: ignore[operator]
        "When a trend condition occurs, the source makes a next day stock claim."
    )
    payload = card.model_dump(mode="json")
    required = {
        "source_id",
        "source_url",
        "source_version",
        "raw_text",
        "quoted_claims",
        "paraphrased_claim",
        "asset_class",
        "forecast_horizon",
        "signal_family",
        "execution_style",
        "required_data",
        "action_rule",
        "risk_assumptions",
        "ambiguity_flags",
        "testability_score",
        "infra_risk",
        "research_priority_score",
        "official_corroboration_source_ids",
        "extraction_model_id",
        "extraction_prompt_version",
        "created_at_utc",
    }
    assert required <= payload.keys()
    assert payload["research_priority_score"] is None


def test_card_rejects_cross_claim_evidence_and_inconsistent_reason_codes(
    build_fixture_card: object,
) -> None:
    card = build_fixture_card(  # type: ignore[operator]
        "When a trend condition occurs, the source makes a next day stock claim."
    )
    invalid_claim = card.model_dump(mode="json")
    invalid_claim["action_rule"]["claim_ids"] = ["segment-outside-source"]
    with pytest.raises(ValidationError, match="field evidence"):
        TradingIdeaCard.model_validate(invalid_claim)

    invalid_reasons = card.model_dump(mode="json")
    invalid_reasons["testability_status"] = "non_testable"
    invalid_reasons["testability_reason_codes"] = ["missing_forecast_horizon"]
    with pytest.raises(ValidationError, match="testability"):
        TradingIdeaCard.model_validate(invalid_reasons)


def test_social_card_rejects_a_bypassed_corroboration_gate(
    build_fixture_card: object,
) -> None:
    card = build_fixture_card(  # type: ignore[operator]
        "If Reddit attention changes, the source makes a next day stock claim.",
        authority=SourceAuthority.SOCIAL,
    )
    bypassed = card.model_dump(mode="json")
    bypassed["contribution_status"] = "not_blocked_by_corroboration"
    with pytest.raises(ValidationError, match="social contribution gate"):
        TradingIdeaCard.model_validate(bypassed)
