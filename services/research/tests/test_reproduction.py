from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AuthorizedMappingIdentity,
    SnapshotBundle,
    SnapshotRequestParameters,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import QualityAcceptedResult, run_mandatory_data_quality
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fable5_research.canonical import (
    PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
    PHASE6_FEATURE_ROW_HASH_DOMAIN,
    PHASE6_FEATURE_ROW_NAMESPACE,
    PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
    PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
    PHASE6_SCORE_HASH_DOMAIN,
    PHASE6_SCORE_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
    PHASE6_LEDGER_CELL_NAMESPACE,
    PHASE6_MODEL_OUTPUT_SET_NAMESPACE,
    PreparedResearchPipeline,
    ResearchConfigurationId,
    ResearchFeatureRow,
    ResearchModelOutputSet,
    ResearchScoreOutput,
    frozen_trial_allocation,
)
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.reproduction import (
    PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN,
    PHASE6_REPRODUCTION_AUDIT_NAMESPACE,
    PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
    PreparedPipelineReproductionAudit,
    PreparedPipelineReproductionMismatch,
    verify_prepared_pipeline_reproduction,
)
from pydantic import ValidationError

_SOURCE_ID = UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd")
_QUANTUM = Decimal("0.000000000001")


def _mapping() -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc"),
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase6-reproduction-tests-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=(_SOURCE_ID,),
    )


def _snapshots(mapping: AuthorizedMappingIdentity) -> tuple[SnapshotBundle, ...]:
    adapter, catalog = resolve_phase6_synthetic_adapter(mapping)
    snapshots: list[SnapshotBundle] = []
    for capability in sorted(AUTHORIZED_CAPABILITIES[mapping.canonical_family], key=str):
        request = SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=datetime(2022, 1, 1, tzinfo=UTC),
            capability=capability,
            mock_configuration_id=PHASE6_SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
        )
        quality = run_mandatory_data_quality(
            request=request,
            result=adapter.fetch(capability),
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            catalog=catalog,
        )
        assert isinstance(quality, QualityAcceptedResult)
        candidate = build_snapshot_candidate(
            mapping=mapping,
            request=request,
            profile=adapter.profile,
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            batch=quality.batch,
        )
        assert isinstance(candidate, SnapshotCandidate)
        snapshots.append(candidate.bundle)
    return tuple(snapshots)


@pytest.fixture(scope="module")
def prepared_case() -> tuple[tuple[SnapshotBundle, ...], PreparedResearchPipeline]:
    snapshots = _snapshots(_mapping())
    return snapshots, prepare_research_pipeline(ResearchConfigurationId.C_PASS, snapshots)


def _rehash_row(payload: dict[str, object]) -> ResearchFeatureRow:
    features = payload["features"]
    label_references = payload["label_source_references"]
    assert isinstance(features, tuple)
    payload["source_lineage_sha256"] = domain_sha256(
        PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
        {
            "feature_source_references": tuple(
                feature["source_references"] for feature in features
            ),
            "label_source_references": label_references,
        },
    )
    content = {key: value for key, value in payload.items() if key not in {"row_id", "row_sha256"}}
    digest = domain_sha256(PHASE6_FEATURE_ROW_HASH_DOMAIN, content)
    payload["row_id"] = identity(PHASE6_FEATURE_ROW_NAMESPACE, digest)
    payload["row_sha256"] = digest
    return ResearchFeatureRow.model_validate(payload)


def _rehash_score(score: ResearchScoreOutput, row: ResearchFeatureRow) -> ResearchScoreOutput:
    payload = score.model_dump(mode="python")
    payload["feature_row_id"] = row.row_id
    content = {
        key: value for key, value in payload.items() if key not in {"score_id", "output_sha256"}
    }
    digest = domain_sha256(PHASE6_SCORE_HASH_DOMAIN, content)
    payload["score_id"] = identity(PHASE6_SCORE_NAMESPACE, digest)
    payload["output_sha256"] = digest
    return ResearchScoreOutput.model_validate(payload)


def _rehash_cell(cell: dict[str, object]) -> None:
    content = {key: value for key, value in cell.items() if key not in {"cell_id", "cell_sha256"}}
    digest = domain_sha256("phase6-research-ledger-cell-v2", content)
    cell["cell_id"] = identity(PHASE6_LEDGER_CELL_NAMESPACE, digest)
    cell["cell_sha256"] = digest


def _rehash_output_set(payload: dict[str, object]) -> ResearchModelOutputSet:
    content = {
        key: value
        for key, value in payload.items()
        if key not in {"output_set_id", "output_set_sha256"}
    }
    digest = domain_sha256("phase6-phase5-model-output-registry-entry-v2", content)
    payload["output_set_id"] = identity(PHASE6_MODEL_OUTPUT_SET_NAMESPACE, digest)
    payload["output_set_sha256"] = digest
    return ResearchModelOutputSet.model_validate(payload)


def _rehash_pipeline(
    prepared: PreparedResearchPipeline,
    **updates: object,
) -> PreparedResearchPipeline:
    provisional = prepared.model_copy(update={**updates, "pipeline_input_sha256": "0" * 64})
    content = provisional.model_dump(mode="python", exclude={"pipeline_input_sha256"})
    return provisional.model_copy(
        update={
            "pipeline_input_sha256": domain_sha256(
                PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
                content,
            )
        }
    )


def _replace_first_row(
    prepared: PreparedResearchPipeline,
    row: ResearchFeatureRow,
) -> tuple[tuple[ResearchFeatureRow, ...], tuple[ResearchScoreOutput, ...]]:
    rows = (row, *prepared.feature_rows[1:])
    scores = (
        _rehash_score(prepared.scores[0], row),
        *prepared.scores[1:],
    )
    return rows, scores


def _tamper_feature(prepared: PreparedResearchPipeline) -> PreparedResearchPipeline:
    payload = prepared.feature_rows[0].model_dump(mode="python")
    features = payload["features"]
    assert isinstance(features, tuple)
    features[0]["formula_id"] = f"{features[0]['formula_id']}.tampered"
    row = _rehash_row(payload)
    rows, scores = _replace_first_row(prepared, row)
    return _rehash_pipeline(prepared, feature_rows=rows, scores=scores)


def _tamper_label(prepared: PreparedResearchPipeline) -> PreparedResearchPipeline:
    row_payload = prepared.feature_rows[0].model_dump(mode="python")
    row_payload["label_value"] += Decimal("0.01")
    row = _rehash_row(row_payload)
    rows, scores = _replace_first_row(prepared, row)

    output_sets: list[ResearchModelOutputSet] = []
    for original in prepared.model_output_sets:
        payload = original.model_dump(mode="python")
        cells = payload["ledger_cells"]
        assert isinstance(cells, tuple)
        cell = cells[0]
        cell["label_value"] = row.label_value
        cell["label_sha256"] = domain_sha256(
            "phase6-research-ledger-label-v1",
            (
                cell["sample_id"],
                cell["label_value"],
                cell["label_t0_utc"],
                cell["label_t1_utc"],
                cell["label_source_references"],
            ),
        )
        cell["synthetic_gross_return"] = (
            cell["synthetic_research_weight"] * cell["label_value"]
        ).quantize(_QUANTUM)
        _rehash_cell(cell)
        output_sets.append(_rehash_output_set(payload))
    return _rehash_pipeline(
        prepared,
        feature_rows=rows,
        scores=scores,
        model_output_sets=tuple(output_sets),
    )


def _tamper_reference(prepared: PreparedResearchPipeline) -> PreparedResearchPipeline:
    payload = prepared.feature_rows[0].model_dump(mode="python")
    features = payload["features"]
    assert isinstance(features, tuple)
    references = features[0]["source_references"]
    references[0]["source_record_id"] = f"{references[0]['source_record_id']}.tampered"
    row = _rehash_row(payload)
    rows, scores = _replace_first_row(prepared, row)
    return _rehash_pipeline(prepared, feature_rows=rows, scores=scores)


def _tamper_model_output(prepared: PreparedResearchPipeline) -> PreparedResearchPipeline:
    payload = prepared.model_output_sets[0].model_dump(mode="python")
    outputs = payload["outputs"]
    cells = payload["ledger_cells"]
    assert isinstance(outputs, tuple)
    assert isinstance(cells, tuple)
    outputs[0]["output_value"] += Decimal("0.125")
    values = tuple(sorted((item["sample_id"], item["output_value"]) for item in outputs))
    output_sha256 = domain_sha256(PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN, values)
    payload["model_output_sha256"] = output_sha256
    for cell in cells:
        cell["model_output_sha256"] = output_sha256
        if cell["sample_id"] == outputs[0]["sample_id"]:
            cell["model_output"] = outputs[0]["output_value"]
            weight, rule = frozen_trial_allocation(
                trial_key=cell["trial_key"],
                model_id=cell["model_id"],
                sample_id=cell["sample_id"],
                model_output=cell["model_output"],
            )
            cell["synthetic_research_weight"] = weight
            cell["allocation_rule_id"] = rule
            cell["return_status"] = "observed" if weight == 1 else "no_trade"
            cell["synthetic_gross_return"] = (weight * cell["label_value"]).quantize(_QUANTUM)
        _rehash_cell(cell)
    output_set = _rehash_output_set(payload)
    output_sets = (output_set, *prepared.model_output_sets[1:])
    return _rehash_pipeline(prepared, model_output_sets=output_sets)


def test_exact_source_replay_returns_deterministic_hash_bound_audit(
    prepared_case: tuple[tuple[SnapshotBundle, ...], PreparedResearchPipeline],
) -> None:
    snapshots, prepared = prepared_case

    first = verify_prepared_pipeline_reproduction(
        ResearchConfigurationId.C_PASS,
        snapshots,
        prepared,
    )
    second = verify_prepared_pipeline_reproduction(
        ResearchConfigurationId.C_PASS,
        snapshots,
        prepared,
    )

    assert first == second
    assert first.exact_match is True
    assert first.supplied_payload_sha256 == first.reproduced_payload_sha256
    assert first.supplied_pipeline_input_sha256 == prepared.pipeline_input_sha256
    assert first.audit_id == identity(PHASE6_REPRODUCTION_AUDIT_NAMESPACE, first.audit_sha256)
    assert first.snapshot_set_sha256 == domain_sha256(
        PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
        first.snapshot_bindings,
    )


@pytest.mark.parametrize(
    "tamper",
    (_tamper_feature, _tamper_label, _tamper_reference, _tamper_model_output),
    ids=("feature", "label", "source-reference", "model-output"),
)
def test_coherently_rehashed_preparation_tampering_fails_source_reproduction(
    prepared_case: tuple[tuple[SnapshotBundle, ...], PreparedResearchPipeline],
    tamper: Callable[[PreparedResearchPipeline], PreparedResearchPipeline],
) -> None:
    snapshots, prepared = prepared_case
    altered = tamper(prepared)
    assert altered.pipeline_input_sha256 == domain_sha256(
        PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
        altered.model_dump(mode="python", exclude={"pipeline_input_sha256"}),
    )

    with pytest.raises(PreparedPipelineReproductionMismatch) as raised:
        verify_prepared_pipeline_reproduction(
            ResearchConfigurationId.C_PASS,
            snapshots,
            altered,
        )

    assert raised.value.reason_code == "prepared_pipeline_source_reproduction_mismatch"
    assert raised.value.supplied_payload_sha256 != raised.value.reproduced_payload_sha256


def test_reproduction_audit_rejects_coherently_rehashed_false_success(
    prepared_case: tuple[tuple[SnapshotBundle, ...], PreparedResearchPipeline],
) -> None:
    snapshots, prepared = prepared_case
    audit = verify_prepared_pipeline_reproduction(
        ResearchConfigurationId.C_PASS,
        snapshots,
        prepared,
    )
    payload = audit.model_dump(mode="python")
    payload["snapshot_set_sha256"] = "f" * 64
    content = {
        key: value for key, value in payload.items() if key not in {"audit_id", "audit_sha256"}
    }
    digest = domain_sha256(PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN, content)
    payload["audit_id"] = identity(PHASE6_REPRODUCTION_AUDIT_NAMESPACE, digest)
    payload["audit_sha256"] = digest

    with pytest.raises(ValidationError, match="snapshot-set hash"):
        PreparedPipelineReproductionAudit.model_validate(payload)
