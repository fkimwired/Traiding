"""Phase 5 canonical identities, isolated by explicit hash domains."""

from __future__ import annotations

from uuid import UUID

from fable5_data.canonical import canonical_json_bytes, domain_sha256, uuid_from_sha256

PHASE5_POLICY_HASH_DOMAIN = "phase5-evaluation-policy-v1"
PHASE5_FEATURE_HASH_DOMAIN = "phase5-feature-specification-v1"
PHASE5_LABEL_HASH_DOMAIN = "phase5-label-specification-v1"
PHASE5_FIXTURE_HASH_DOMAIN = "phase5-synthetic-evaluation-fixture-v1"
PHASE5_REQUEST_HASH_DOMAIN = "phase5-evaluation-request-v1"
PHASE5_CONFIG_HASH_DOMAIN = "phase5-evaluation-config-v1"
PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN = "phase5-snapshot-bundle-v1"
PHASE5_REPORT_SNAPSHOT_HASH_DOMAIN = "phase5-report-snapshot-v1"
PHASE5_ARTIFACT_HASH_DOMAIN = "phase5-evaluation-artifact-v1"
PHASE5_TRIAL_HASH_DOMAIN = "phase5-trial-v1"
PHASE5_FOLD_HASH_DOMAIN = "phase5-fold-v1"
PHASE5_FIT_HASH_DOMAIN = "phase5-preprocessing-fit-v1"
PHASE5_LEDGER_HASH_DOMAIN = "phase5-ledger-entry-v1"
PHASE5_COST_HASH_DOMAIN = "phase5-cost-entry-v1"
PHASE5_GATE_HASH_DOMAIN = "phase5-gate-result-v1"
PHASE5_SAMPLE_HASH_DOMAIN = "phase5-synthetic-sample-v1"
PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN = "phase5-sample-source-lineage-v1"
PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN = "phase5-derived-dependency-graph-v1"
PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN = "phase5-leakage-evidence-v1"
PHASE5_TRAIN_IDS_HASH_DOMAIN = "phase5-preprocessing-train-ids-v1"
PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN = "phase5-train-only-fit-record-v1"

PHASE5_ARTIFACT_NAMESPACE = UUID("144bb1ef-6882-57d4-868e-ac93cc8c9a51")
PHASE5_POLICY_NAMESPACE = UUID("2899a21e-786a-50bf-a74f-4ad5dbd79d98")
PHASE5_FEATURE_NAMESPACE = UUID("2d2bb9b0-0c1f-57c9-906d-f3e69e75d115")
PHASE5_LABEL_NAMESPACE = UUID("4ded680d-fd4b-5eed-b28e-af905bb854d8")
PHASE5_TRIAL_NAMESPACE = UUID("2df5e771-dad0-54c7-b839-244ca08e38d1")
PHASE5_FOLD_NAMESPACE = UUID("31578e87-cd9e-5915-8e3a-fb8efc561f6f")
PHASE5_FIT_NAMESPACE = UUID("0b37f89d-bb03-5dd1-9047-8c77db79455d")
PHASE5_LEDGER_NAMESPACE = UUID("220c8d7e-72a1-52ea-b79f-a17ecf3f5f84")
PHASE5_COST_NAMESPACE = UUID("c23dc9b2-9af7-5c90-af04-26815c5f8796")
PHASE5_GATE_NAMESPACE = UUID("78999d40-5a65-5622-ac05-b31b32cd79ad")
PHASE5_REPORT_SNAPSHOT_NAMESPACE = UUID("39e65413-c8ba-59ac-b15c-4d21a72e6e14")


def canonical_json_text(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def identity(namespace: UUID, sha256: str) -> UUID:
    return uuid_from_sha256(namespace, sha256)


__all__ = [
    "PHASE5_ARTIFACT_HASH_DOMAIN",
    "PHASE5_ARTIFACT_NAMESPACE",
    "PHASE5_CONFIG_HASH_DOMAIN",
    "PHASE5_COST_HASH_DOMAIN",
    "PHASE5_COST_NAMESPACE",
    "PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN",
    "PHASE5_FEATURE_HASH_DOMAIN",
    "PHASE5_FEATURE_NAMESPACE",
    "PHASE5_FIT_HASH_DOMAIN",
    "PHASE5_FIT_NAMESPACE",
    "PHASE5_FIXTURE_HASH_DOMAIN",
    "PHASE5_FOLD_HASH_DOMAIN",
    "PHASE5_FOLD_NAMESPACE",
    "PHASE5_GATE_HASH_DOMAIN",
    "PHASE5_GATE_NAMESPACE",
    "PHASE5_LABEL_HASH_DOMAIN",
    "PHASE5_LABEL_NAMESPACE",
    "PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN",
    "PHASE5_LEDGER_HASH_DOMAIN",
    "PHASE5_LEDGER_NAMESPACE",
    "PHASE5_POLICY_HASH_DOMAIN",
    "PHASE5_POLICY_NAMESPACE",
    "PHASE5_REPORT_SNAPSHOT_HASH_DOMAIN",
    "PHASE5_REPORT_SNAPSHOT_NAMESPACE",
    "PHASE5_REQUEST_HASH_DOMAIN",
    "PHASE5_SAMPLE_HASH_DOMAIN",
    "PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN",
    "PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN",
    "PHASE5_TRAIN_IDS_HASH_DOMAIN",
    "PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN",
    "PHASE5_TRIAL_HASH_DOMAIN",
    "PHASE5_TRIAL_NAMESPACE",
    "canonical_json_text",
    "domain_sha256",
    "identity",
]
