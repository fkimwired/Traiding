from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    domain_sha256,
)
from fable5_paper.contracts import (
    PaperCheckCode,
    PaperSimulationArtifact,
    PaperSimulationCheck,
    PaperSimulationOutcome,
)
from fable5_paper.evidence import (
    PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
    LocalSimulationEvidenceBundle,
    build_local_simulation_evidence_bundle,
)
from fable5_paper.repository import PaperArtifactNotFound
from fable5_paper.workflow import PaperSimulationWorkflow, PaperWorkflowConflict
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "services/frontend/e2e/fixtures"
FIXTURE_HASHES = {
    "phase10-completed.json": ("8ad868297ec060d00067a5e17e40df83123a306898bfd9eacd869d0af543647c"),
    "phase10-blocked.json": ("35ca33153e7c46a6d0d7154b894020a0db8e1c4ac67d41db1869289771c43f3f"),
}


def _artifact(name: str = "phase10-completed.json") -> PaperSimulationArtifact:
    return PaperSimulationArtifact.model_validate(
        json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    )


def _forge_check_evidence(
    artifact: PaperSimulationArtifact,
    *,
    code: PaperCheckCode,
    evidence_sha256s: tuple[str, ...],
) -> PaperSimulationArtifact:
    checks = list(artifact.checks)
    index = next(index for index, item in enumerate(checks) if item.code is code)
    check_payload = checks[index].model_dump(mode="python", exclude={"check_sha256"})
    check_payload["evidence_sha256s"] = tuple(sorted(set(evidence_sha256s)))
    checks[index] = PaperSimulationCheck.model_validate(
        {
            **check_payload,
            "check_sha256": domain_sha256(PHASE10_CHECK_HASH_DOMAIN, check_payload),
        }
    )
    artifact_payload = artifact.model_dump(
        mode="python",
        exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"},
    )
    artifact_payload["checks"] = tuple(checks)
    return PaperSimulationArtifact.model_validate(
        {
            **artifact_payload,
            "simulation_run_id": artifact.simulation_run_id,
            "artifact_sha256": domain_sha256(
                PHASE10_ARTIFACT_HASH_DOMAIN,
                artifact_payload,
            ),
            "created_at_utc": artifact.created_at_utc,
        }
    )


@pytest.mark.parametrize(
    ("fixture_name", "outcome", "ledger_count"),
    (
        ("phase10-completed.json", PaperSimulationOutcome.SIMULATED_COMPLETE, 1),
        ("phase10-blocked.json", PaperSimulationOutcome.BLOCKED, 0),
    ),
)
def test_completed_and_blocked_bundles_are_exact_repeatable_projections(
    fixture_name: str,
    outcome: PaperSimulationOutcome,
    ledger_count: int,
) -> None:
    artifact = _artifact(fixture_name)

    first = build_local_simulation_evidence_bundle(artifact)
    second = build_local_simulation_evidence_bundle(artifact)

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.bundle_schema_version == "phase11-local-simulation-evidence-bundle-v1"
    assert first.bundle_sha256 == FIXTURE_HASHES[fixture_name]
    assert first.simulation_run_id == artifact.simulation_run_id
    assert first.simulation_artifact_sha256 == artifact.artifact_sha256
    assert first.simulation == artifact
    assert first.simulation.outcome is outcome
    assert len(first.simulation.ledger_entries) == ledger_count
    payload = first.model_dump(mode="python", exclude={"bundle_sha256"})
    assert first.bundle_sha256 == domain_sha256(
        PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
        payload,
    )


def test_research_check_contains_exact_lineage_and_one_phase5_hash() -> None:
    artifact = _artifact()
    bundle = build_local_simulation_evidence_bundle(artifact)
    research_check = next(
        item
        for item in bundle.simulation.checks
        if item.code is PaperCheckCode.RESEARCH_PREREQUISITES_COMPLETE
    )
    required = {
        artifact.research_artifact_sha256,
        artifact.configuration.research_specification_sha256,
    }

    assert required <= set(research_check.evidence_sha256s)
    assert len(research_check.evidence_sha256s) == 3
    assert len(set(research_check.evidence_sha256s) - required) == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("bundle_sha256", "0" * 64, "complete immutable payload"),
        (
            "simulation_run_id",
            UUID("00000000-0000-4000-8000-000000000011"),
            "identities must bind",
        ),
        ("simulation_artifact_sha256", "1" * 64, "identities must bind"),
    ),
)
def test_bundle_rejects_hash_or_top_level_identity_tampering(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = build_local_simulation_evidence_bundle(_artifact()).model_dump(mode="python")
    payload[field] = value

    with pytest.raises(ValidationError, match=message):
        LocalSimulationEvidenceBundle.model_validate(payload)


def test_bundle_is_strict_and_all_five_fields_are_required() -> None:
    payload = build_local_simulation_evidence_bundle(_artifact()).model_dump(mode="python")
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        LocalSimulationEvidenceBundle.model_validate({**payload, "exported_at_utc": "secret"})
    for field in tuple(payload):
        incomplete = dict(payload)
        incomplete.pop(field)
        with pytest.raises(ValidationError, match="Field required"):
            LocalSimulationEvidenceBundle.model_validate(incomplete)


def test_builder_revalidates_a_forged_nested_artifact() -> None:
    artifact = _artifact()
    forged = artifact.model_copy(update={"artifact_sha256": "0" * 64})

    with pytest.raises(ValidationError, match="artifact hash"):
        build_local_simulation_evidence_bundle(forged)


def test_bundle_rejects_an_internally_rehashed_cross_lineage_check() -> None:
    artifact = _artifact()
    forged = _forge_check_evidence(
        artifact,
        code=PaperCheckCode.SOURCE_APPROVAL_EXACT,
        evidence_sha256s=("0" * 64,),
    )

    with pytest.raises(ValidationError, match="SOURCE_APPROVAL_EXACT evidence"):
        build_local_simulation_evidence_bundle(forged)


def test_bundle_binds_persisted_creation_after_the_decision() -> None:
    artifact = _artifact()
    changed = artifact.model_dump(mode="python")
    changed["created_at_utc"] = artifact.decision_time_utc - timedelta(microseconds=1)
    forged = PaperSimulationArtifact.model_validate(changed)

    with pytest.raises(ValidationError, match="decision time cannot follow"):
        build_local_simulation_evidence_bundle(forged)


def test_workflow_getter_reads_once_without_clock_gateway_or_write() -> None:
    artifact = _artifact()
    simulations = MagicMock()
    simulations.get_simulation.return_value = artifact
    evidence = MagicMock()
    clock = MagicMock(side_effect=AssertionError("read projection called a clock"))
    workflow = PaperSimulationWorkflow(
        evidence=evidence,
        simulations=simulations,
        phase10_code_version_git_sha="a" * 40,
        clock=clock,
    )

    bundle = workflow.get_simulation_evidence_bundle(artifact.simulation_run_id)

    assert bundle.simulation == artifact
    simulations.get_simulation.assert_called_once_with(artifact.simulation_run_id)
    simulations.create_simulation.assert_not_called()
    simulations.serialized_creation.assert_not_called()
    simulations.list_simulations.assert_not_called()
    assert evidence.mock_calls == []
    clock.assert_not_called()


def test_workflow_preserves_missing_and_wraps_projection_conflicts() -> None:
    artifact = _artifact()
    missing = PaperArtifactNotFound("secret missing simulation")
    simulations = MagicMock()
    workflow = PaperSimulationWorkflow(
        evidence=MagicMock(),
        simulations=simulations,
        phase10_code_version_git_sha="a" * 40,
    )
    simulations.get_simulation.side_effect = missing
    with pytest.raises(PaperArtifactNotFound) as caught:
        workflow.get_simulation_evidence_bundle(artifact.simulation_run_id)
    assert caught.value is missing

    simulations.get_simulation.side_effect = None
    simulations.get_simulation.return_value = artifact.model_copy(
        update={"artifact_sha256": "0" * 64}
    )
    with pytest.raises(PaperWorkflowConflict, match="cannot be projected"):
        workflow.get_simulation_evidence_bundle(artifact.simulation_run_id)
