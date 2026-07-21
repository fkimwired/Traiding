from __future__ import annotations

import json

from fable5_data.phase25 import canonical as c
from fable5_data.phase25.package import (
    build_phase25_package,
    canonical_phase25_package_bytes,
)


def test_phase25_builder_is_deterministic_and_matches_committed_artifact() -> None:
    first = canonical_phase25_package_bytes()
    assert first == canonical_phase25_package_bytes()
    assert first.endswith(b"\n") and b"\r" not in first
    assert (
        json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")).encode() + b"\n"
        == first
    )


def test_phase25_source_registry_is_exact_and_license_aware() -> None:
    artifact = build_phase25_package()
    revisions = {row.code: row.inspected_revision for row in artifact.source_evidence}
    licenses = {row.code: row.software_license for row in artifact.source_evidence}
    assert revisions["YFINANCE"] == "38c73ce33fb1ee77d37a0998c95c06e60356298e"
    assert revisions["OPENBB"] == "3e071fcc2cd9f891cac6040ae60296dba76dab46"
    assert revisions["FINROBOT"] == "297a8d28d099be328c8a8eb658b4f782b93f3651"
    assert revisions["TRADINGAGENTS"] == "a33fd4c0f134485a43553a2c23a63cb14adbd88f"
    assert licenses == {
        "YFINANCE": "Apache-2.0",
        "OPENBB": "AGPL-3.0-only",
        "FINROBOT": "Apache-2.0",
        "TRADINGAGENTS": "Apache-2.0",
        "PHILADELPHIA_FED_RTDSM_PAGE": "UNSPECIFIED_PROVIDER_CONTENT",
        "PHILADELPHIA_FED_ONLINE_TERMS": "UNSPECIFIED_PROVIDER_CONTENT",
        "PHILADELPHIA_FED_PCPI_DOCUMENTATION": "UNSPECIFIED_PROVIDER_CONTENT",
        "PHILADELPHIA_FED_RELEASE_VALUES_DOCUMENTATION": "UNSPECIFIED_PROVIDER_CONTENT",
        "YAHOO_API_TERMS": "PROPRIETARY_TERMS",
        "YAHOO_GENERAL_TERMS": "PROPRIETARY_TERMS",
    }
    assert all(row.source_sha256 for row in artifact.source_evidence)


def test_phase25_patterns_are_provider_neutral_documentation_only() -> None:
    artifact = build_phase25_package()
    assert [row.code for row in artifact.adapter_patterns] == [
        row[0] for row in c.PHASE25_PATTERN_ROWS
    ]
    assert all(
        row.status.value == "DOCUMENTED_NOT_IMPLEMENTED" for row in artifact.adapter_patterns
    )
    assert artifact.yahoo_rights_state == "RIGHTS_UNVERIFIED"
    assert not artifact.yfinance_dependency_added
    assert not artifact.production_adapter_activated
    assert not artifact.provider_observations_downloaded
    assert artifact.llm_trade_decisions_prohibited


def test_phase25_audit_identity_and_phase24_lineage_are_frozen() -> None:
    artifact = build_phase25_package()
    assert artifact.config_sha256 == artifact.policy_sha256 == c.PHASE25_POLICY_SHA256
    assert artifact.phase24_merge_commit_sha == c.PHASE25_PHASE24_MERGE_COMMIT_SHA
    assert artifact.phase24_merge_tree_sha == c.PHASE25_PHASE24_MERGE_TREE_SHA
    assert artifact.generation_git_sha == c.PHASE25_GENERATION_GIT_SHA
    assert artifact.random_seed == 0 and artifact.trial_count == 0
    assert str(artifact.generated_at_utc).endswith("+00:00")
    assert artifact.source_snapshot_id and artifact.evidence_snapshot_id
