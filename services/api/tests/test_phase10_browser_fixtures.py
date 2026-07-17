from __future__ import annotations

from pathlib import Path

from fable5_extraction.models import TradingIdeaCard
from fable5_paper.contracts import PaperSimulationArtifact, PaperSimulationOutcome
from fable5_risk.contracts import ApprovalAssessmentArtifact, ApprovalAssessmentOutcome

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "fixtures"


def _artifact(name: str) -> PaperSimulationArtifact:
    return PaperSimulationArtifact.model_validate_json(
        (FIXTURE_DIRECTORY / name).read_text(encoding="utf-8")
    )


def _assessment(name: str) -> ApprovalAssessmentArtifact:
    return ApprovalAssessmentArtifact.model_validate_json(
        (FIXTURE_DIRECTORY / name).read_text(encoding="utf-8")
    )


def test_phase10_browser_fixtures_are_complete_domain_valid_artifacts() -> None:
    completed = _artifact("phase10-completed.json")
    blocked = _artifact("phase10-blocked.json")
    source_assessment = _assessment("phase10-source-assessment.json")
    blocked_assessment = _assessment("phase10-blocked-assessment.json")
    card = TradingIdeaCard.model_validate_json(
        (FIXTURE_DIRECTORY / "phase10-synthetic-card.json").read_text(encoding="utf-8")
    )

    assert completed.outcome is PaperSimulationOutcome.SIMULATED_COMPLETE
    assert len(completed.ledger_entries) == 1
    assert blocked.outcome is PaperSimulationOutcome.BLOCKED
    assert blocked.ledger_entries == ()
    assert completed.source_assessment_id == blocked.source_assessment_id
    assert source_assessment.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
    assert blocked_assessment.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert card.synthetic_fixture is True
    assert completed.source_assessment_id == source_assessment.assessment_id
    assert completed.source_assessment_artifact_sha256 == source_assessment.artifact_sha256
    assert completed.transition_assessment_id == source_assessment.assessment_id
    assert completed.transition_assessment_artifact_sha256 == source_assessment.artifact_sha256
    assert blocked.transition_assessment_id == blocked_assessment.assessment_id
    assert blocked.transition_assessment_artifact_sha256 == blocked_assessment.artifact_sha256
    assert (
        blocked.decision_time_utc
        == blocked.created_at_utc
        == blocked.transition_revalidation_proof.decision_time_utc
        == blocked_assessment.created_at_utc
    )
    assert (
        blocked.transition_currentness_state_sha256 == blocked_assessment.currentness_state_sha256
    )
    assert blocked.transition_revocation_set_sha256 == blocked_assessment.revocation_set_sha256
    assert source_assessment.created_at_utc <= blocked.decision_time_utc
    assert completed.simulation_idempotency_key == "11111111-1111-4111-8111-111111111110"
    assert blocked.simulation_idempotency_key == "22222222-2222-4222-8222-222222222220"
