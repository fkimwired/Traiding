"""Deterministic source-reproduction preflight for prepared Phase 6 research."""

from __future__ import annotations

from fable5_data.contracts import SnapshotBundle

from fable5_research.canonical import (
    PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN,
    PHASE6_REPRODUCTION_AUDIT_NAMESPACE,
    PHASE6_REPRODUCTION_PAYLOAD_HASH_DOMAIN,
    PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
    PreparedPipelineReproductionAudit,
    PreparedResearchPipeline,
    ResearchConfigurationId,
)
from fable5_research.preparation import prepare_research_pipeline


class PreparedPipelineReproductionMismatch(ValueError):
    """Raised when persisted preparation cannot be reproduced exactly from source."""

    reason_code = "prepared_pipeline_source_reproduction_mismatch"

    def __init__(
        self,
        *,
        supplied_payload_sha256: str,
        reproduced_payload_sha256: str,
    ) -> None:
        self.supplied_payload_sha256 = supplied_payload_sha256
        self.reproduced_payload_sha256 = reproduced_payload_sha256
        super().__init__(
            "prepared research pipeline does not exactly reproduce from immutable snapshots"
        )


def _payload_sha256(pipeline: PreparedResearchPipeline) -> str:
    return domain_sha256(PHASE6_REPRODUCTION_PAYLOAD_HASH_DOMAIN, pipeline)


def verify_prepared_pipeline_reproduction(
    configuration_id: ResearchConfigurationId,
    snapshots: tuple[SnapshotBundle, ...],
    supplied: PreparedResearchPipeline,
) -> PreparedPipelineReproductionAudit:
    """Recompute preparation and fail closed unless every supplied field is exact."""

    reproduced = prepare_research_pipeline(configuration_id, snapshots)
    supplied_payload_sha256 = _payload_sha256(supplied)
    reproduced_payload_sha256 = _payload_sha256(reproduced)
    if supplied != reproduced or canonical_json_bytes(supplied) != canonical_json_bytes(reproduced):
        raise PreparedPipelineReproductionMismatch(
            supplied_payload_sha256=supplied_payload_sha256,
            reproduced_payload_sha256=reproduced_payload_sha256,
        )

    snapshot_bindings = tuple(
        sorted(
            supplied.snapshot_bindings,
            key=lambda item: (str(item.snapshot_id), item.snapshot_sha256),
        )
    )
    content = {
        "schema_version": "phase6-prepared-source-reproduction-audit-v1",
        "configuration_id": configuration_id,
        "snapshot_bindings": snapshot_bindings,
        "snapshot_set_sha256": domain_sha256(
            PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
            snapshot_bindings,
        ),
        "supplied_pipeline_input_sha256": supplied.pipeline_input_sha256,
        "reproduced_pipeline_input_sha256": reproduced.pipeline_input_sha256,
        "supplied_payload_sha256": supplied_payload_sha256,
        "reproduced_payload_sha256": reproduced_payload_sha256,
        "exact_match": True,
    }
    audit_sha256 = domain_sha256(PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN, content)
    return PreparedPipelineReproductionAudit.model_validate(
        {
            **content,
            "audit_id": identity(PHASE6_REPRODUCTION_AUDIT_NAMESPACE, audit_sha256),
            "audit_sha256": audit_sha256,
        }
    )


__all__ = [
    "PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN",
    "PHASE6_REPRODUCTION_AUDIT_NAMESPACE",
    "PHASE6_REPRODUCTION_PAYLOAD_HASH_DOMAIN",
    "PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN",
    "PreparedPipelineReproductionAudit",
    "PreparedPipelineReproductionMismatch",
    "verify_prepared_pipeline_reproduction",
]
