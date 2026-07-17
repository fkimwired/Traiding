"""Pure, hash-bound Phase 11 projections of immutable Phase 10 simulations."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import model_validator

from fable5_paper.canonical import domain_sha256
from fable5_paper.contracts import (
    SHA256,
    PaperCheckCode,
    PaperSimulationArtifact,
    StrictModel,
)

PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_SCHEMA_VERSION: Literal[
    "phase11-local-simulation-evidence-bundle-v1"
] = "phase11-local-simulation-evidence-bundle-v1"
PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN = "phase11-local-simulation-evidence-bundle-v1"


def _ordered_evidence(*values: str) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _bundle_payload(simulation: PaperSimulationArtifact) -> dict[str, object]:
    return {
        "bundle_schema_version": PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "simulation_run_id": simulation.simulation_run_id,
        "simulation_artifact_sha256": simulation.artifact_sha256,
        "simulation": simulation,
    }


def _validate_check_evidence(simulation: PaperSimulationArtifact) -> None:
    configuration = simulation.configuration
    proof = simulation.transition_revalidation_proof
    checks = {item.code: item for item in simulation.checks}
    code_evidence = domain_sha256(
        "phase10-code-version-evidence-v1",
        simulation.phase10_code_version_git_sha,
    )
    expected = {
        PaperCheckCode.SOURCE_APPROVAL_EXACT: _ordered_evidence(
            simulation.source_assessment_artifact_sha256,
            simulation.phase6_lineage_sha256,
        ),
        PaperCheckCode.TRANSITION_APPROVAL_FRESH: _ordered_evidence(
            simulation.transition_assessment_artifact_sha256,
            simulation.transition_currentness_state_sha256,
            simulation.transition_revocation_set_sha256,
            proof.revalidation_proof_sha256,
        ),
        PaperCheckCode.SIMULATION_CONFIGURATION_EXACT: _ordered_evidence(
            configuration.configuration_sha256,
            simulation.research_artifact_sha256,
        ),
        PaperCheckCode.RISK_CONTEXT_EXACT: _ordered_evidence(
            simulation.risk_input_sha256,
            configuration.configuration_sha256,
        ),
        PaperCheckCode.COST_SLIPPAGE_COMPLETE: _ordered_evidence(
            configuration.research_specification_sha256,
            configuration.configuration_sha256,
        ),
        PaperCheckCode.LOCAL_BOUNDARY_ENFORCED: _ordered_evidence(
            configuration.configuration_sha256,
            code_evidence,
        ),
    }
    for code, expected_evidence in expected.items():
        if checks[code].evidence_sha256s != expected_evidence:
            raise ValueError(f"{code.value} evidence must derive from the simulation artifact")

    research_evidence = set(checks[PaperCheckCode.RESEARCH_PREREQUISITES_COMPLETE].evidence_sha256s)
    required_research_evidence = {
        simulation.research_artifact_sha256,
        configuration.research_specification_sha256,
    }
    if (
        not required_research_evidence <= research_evidence
        or len(research_evidence) != 3
        or len(research_evidence - required_research_evidence) != 1
    ):
        raise ValueError(
            "research prerequisite evidence must contain the research artifact, specification, "
            "and exactly one Phase 5 hash"
        )


class LocalSimulationEvidenceBundle(StrictModel):
    """Portable deterministic projection of one fully revalidated Phase 10 artifact."""

    bundle_schema_version: Literal["phase11-local-simulation-evidence-bundle-v1"]
    bundle_sha256: SHA256
    simulation_run_id: UUID
    simulation_artifact_sha256: SHA256
    simulation: PaperSimulationArtifact

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        if (
            self.simulation_run_id != self.simulation.simulation_run_id
            or self.simulation_artifact_sha256 != self.simulation.artifact_sha256
        ):
            raise ValueError(
                "evidence bundle identities must bind the exact Phase 10 simulation artifact"
            )
        if self.simulation.decision_time_utc > self.simulation.created_at_utc:
            raise ValueError("simulation decision time cannot follow its persisted creation time")
        _validate_check_evidence(self.simulation)
        payload = self.model_dump(mode="python", exclude={"bundle_sha256"})
        expected_hash = domain_sha256(
            PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
            payload,
        )
        if self.bundle_sha256 != expected_hash:
            raise ValueError("evidence bundle hash must bind its complete immutable payload")
        return self


def build_local_simulation_evidence_bundle(
    simulation: PaperSimulationArtifact,
) -> LocalSimulationEvidenceBundle:
    """Return a deterministic projection without clocks, identities, I/O, or persistence."""

    validated = PaperSimulationArtifact.model_validate(simulation.model_dump(mode="python"))
    payload = _bundle_payload(validated)
    return LocalSimulationEvidenceBundle.model_validate(
        {
            **payload,
            "bundle_sha256": domain_sha256(
                PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
                payload,
            ),
        }
    )


__all__ = [
    "PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN",
    "PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "LocalSimulationEvidenceBundle",
    "build_local_simulation_evidence_bundle",
]
