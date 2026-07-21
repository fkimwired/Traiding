"""Canonical constants for the Phase 24 RTDSM rights-clarification requirements."""

# ruff: noqa: E501 -- canonical policy text is intentionally stored as exact immutable rows.

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE24_ARTIFACT_SCHEMA_VERSION: Final = (
    "phase24-family-a-rtdsm-rights-clarification-requirements-v1"
)
PHASE24_DISCLOSURE_SCHEMA_VERSION: Final = "phase24-family-a-proposed-use-disclosure-v1"
PHASE24_QUESTION_SCHEMA_VERSION: Final = "phase24-family-a-rights-clarification-question-v1"
PHASE24_EVIDENCE_SCHEMA_VERSION: Final = "phase24-family-a-rights-evidence-requirement-v1"
PHASE24_RULE_SCHEMA_VERSION: Final = "phase24-family-a-rights-answer-transition-rule-v1"

PHASE24_ARTIFACT_HASH_DOMAIN: Final = PHASE24_ARTIFACT_SCHEMA_VERSION
PHASE24_DISCLOSURE_HASH_DOMAIN: Final = PHASE24_DISCLOSURE_SCHEMA_VERSION
PHASE24_QUESTION_HASH_DOMAIN: Final = PHASE24_QUESTION_SCHEMA_VERSION
PHASE24_EVIDENCE_HASH_DOMAIN: Final = PHASE24_EVIDENCE_SCHEMA_VERSION
PHASE24_RULE_HASH_DOMAIN: Final = PHASE24_RULE_SCHEMA_VERSION
PHASE24_DISCLOSURES_MANIFEST_HASH_DOMAIN: Final = "phase24-proposed-use-disclosures-manifest-v1"
PHASE24_QUESTIONS_MANIFEST_HASH_DOMAIN: Final = "phase24-rights-clarification-questions-manifest-v1"
PHASE24_EVIDENCE_MANIFEST_HASH_DOMAIN: Final = "phase24-rights-evidence-requirements-manifest-v1"
PHASE24_RULES_MANIFEST_HASH_DOMAIN: Final = "phase24-rights-answer-transition-rules-manifest-v1"
PHASE24_POLICY_ID: Final = "phase24-family-a-rtdsm-rights-clarification-requirements-policy-v1"
PHASE24_POLICY_HASH_DOMAIN: Final = PHASE24_POLICY_ID
PHASE24_ARTIFACT_NAMESPACE: Final = UUID("989d2bb7-7167-50b7-95b9-b61fac578b27")

PHASE24_ACCEPTED_PHASE23_COMMIT_SHA: Final = "d8d8d63a79457c7a54e0a3738a75f4eb613c602f"
PHASE24_ACCEPTED_PHASE23_TREE_SHA: Final = "4f3da35d31f352ea92d5f715149e0e439a57af3b"
PHASE24_PHASE23_MERGE_COMMIT_SHA: Final = "53d9f8641d98c729447661af9b7e561073a52226"
PHASE24_PHASE23_ARTIFACT_ID: Final = "e4fbd5af-c5ad-51fb-92cb-7308fafd017a"
PHASE24_PHASE23_ARTIFACT_SHA256: Final = (
    "aafb6deadff7b4cd4f9b4e7c98c8ac31f0d957a60b1d5be59f3d7ebf2679cd2c"
)
PHASE24_PHASE23_POLICY_SHA256: Final = (
    "624c553bc1a7777e33634464743b4e0d37115136afedca81c2cdbc43c819dd16"
)
PHASE24_PHASE23_FINDINGS_MANIFEST_SHA256: Final = (
    "43e8f5dc60ce6de114510b8c763d28da371b9d57a82854c62e4b6b746ffcb06b"
)
PHASE24_PHASE23_REQUIREMENTS_MANIFEST_SHA256: Final = (
    "17bb6f314ed053f6a4d7683af361e151deb948805b35009593a823967f85ae9f"
)
PHASE24_PRODUCT_CODE: Final = "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
PHASE24_PHASE22_PRODUCT_SHA256: Final = (
    "59a206777d9f48737c11c557ffdabd5a80c66159822356a7726ed314436da067"
)
PHASE24_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE24_FROZEN_AT_UTC: Final = "2026-07-21T06:00:00.000000Z"
PHASE24_OUTCOME: Final = "BLOCKED"
PHASE24_REQUIREMENTS_STATE: Final = "RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN"
PHASE24_AGGREGATE_CONCLUSION: Final = (
    "BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION"
)
PHASE24_BLOCK_REASON: Final = (
    "Phase 23 found that public terms do not resolve Fable5's exact persistent automated use. "
    "No authenticated product-specific answer or independently verified rights evidence is present."
)

# code, proposed disclosure
PHASE24_DISCLOSURE_ROWS: Final = (
    (
        "PURPOSE_AND_ENVIRONMENT",
        "Internal quantitative research and simulated paper trading only; no live trading, advice, or customer order routing.",
    ),
    (
        "PRODUCT_AND_SERIES_SCOPE",
        "Philadelphia Fed RTDSM is a candidate only; the exact series, delivery, account, and entitlement remain unselected.",
    ),
    (
        "AUTOMATED_ACCESS_PATTERN",
        "Potential scheduled machine access would occur only at an approved frequency and under documented access limits.",
    ),
    (
        "PERSISTENT_STORAGE_AND_BACKUPS",
        "The proposed use may require persistent point-in-time snapshots, reproducible versions, backups, and audit lineage.",
    ),
    (
        "AUTOMATED_MODEL_PROCESSING",
        "The proposed use may feed deterministic feature generation and model evaluation; an LLM would not produce trade instructions.",
    ),
    (
        "DERIVED_OUTPUTS",
        "The proposed use may produce features, diagnostics, models, aggregate reports, and hash-bound audit evidence.",
    ),
    (
        "DISPLAY_AND_REDISTRIBUTION",
        "No raw-data public display or redistribution is proposed, but any internal sharing or derived display still requires explicit scope.",
    ),
    (
        "RETENTION_DELETION_AND_REVOCATION",
        "The implementation must support any verified retention, deletion, cessation, attribution, and revalidation conditions.",
    ),
)

# code, Phase 23 field, exact question
PHASE24_QUESTION_ROWS: Final = (
    (
        "PERSISTENT_STORAGE",
        "persistent_storage",
        "May Fable5 persist exact RTDSM delivery bytes and normalized point-in-time snapshots, including reproducibility copies and backups?",
    ),
    (
        "AUTOMATED_MODEL_INTERNAL_USE",
        "automated_model_internal_use",
        "May Fable5 use RTDSM data in automated internal feature generation, statistical modeling, backtesting, and simulated paper-trading research?",
    ),
    (
        "DERIVED_DATA_AND_MODEL_ARTIFACTS",
        "derived_data",
        "May Fable5 retain and use derived features, aggregates, diagnostics, model parameters, and audit hashes after processing RTDSM data?",
    ),
    (
        "RETENTION_DELETION",
        "retention_deletion",
        "What retention limits, deletion deadlines, backup handling, and post-termination obligations apply to raw and derived artifacts?",
    ),
    (
        "REDISTRIBUTION_AND_DISPLAY",
        "redistribution",
        "What internal sharing, user display, export, publication, and redistribution restrictions apply to raw values and derived outputs?",
    ),
    (
        "ATTRIBUTION",
        "attribution",
        "What source labels, notices, citations, or attribution text are required for stored data and derived outputs?",
    ),
    (
        "THIRD_PARTY_BLS_CONTENT",
        "third_party_content",
        "Does the permission cover BLS-originated PCPI content for the exact proposed uses, or is separate rights-holder permission required?",
    ),
    (
        "AUTOMATED_ACCESS_AND_LOAD",
        "access_load",
        "Which delivery method, automated access pattern, frequency, concurrency, and rate or bulk-download limits are authorized?",
    ),
    (
        "REVOCATION_AND_CURRENTNESS",
        "revocation_currentness",
        "What effective date, term version, change notice, revocation trigger, cure period, and revalidation cadence govern the permission?",
    ),
    (
        "AUTHORITY_AND_PRODUCT_SCOPE",
        "operational_use_cleared",
        "Which rights-holding entity and authorized representative can bind the exact product, series, delivery, account, users, and proposed use?",
    ),
)

# code, requirement, acceptable evidence
PHASE24_EVIDENCE_ROWS: Final = (
    (
        "AUTHENTICATED_RIGHTS_HOLDER_IDENTITY",
        "Identify the rights-holding entity and authority of the person or instrument providing the answer.",
        "Executed agreement or authenticated written response from the provider or applicable rights holder.",
    ),
    (
        "EXACT_PRODUCT_SERIES_DELIVERY_SCOPE",
        "Bind the answer to the exact product, series, delivery method, account or user scope, and intended-use disclosure set.",
        "Product-specific schedule, entitlement, order form, license exhibit, or authenticated scope confirmation.",
    ),
    (
        "EXPLICIT_INTENDED_USE_COVERAGE",
        "Resolve every clarification question with an explicit permitted, prohibited, or conditional answer.",
        "Clause-level executed terms or authenticated written answers covering every frozen question.",
    ),
    (
        "EFFECTIVE_TERMS_AND_CURRENTNESS",
        "Record effective date, governing version, precedence, expiry, renewal, and currentness evidence.",
        "Dated executed terms plus independently authenticated currentness or a dated rights-holder confirmation.",
    ),
    (
        "THIRD_PARTY_RIGHTS_COVERAGE",
        "Resolve whether BLS-originated content is included or requires separate permission.",
        "Express upstream-rights coverage or authenticated permission from the applicable third-party rights holder.",
    ),
    (
        "REVOCATION_RETENTION_AND_DELETION",
        "Make revocation, notice, retention, deletion, backup, attribution, audit-retention, and cessation obligations enforceable.",
        "Executed clauses or authenticated written conditions that can be translated into fail-closed controls.",
    ),
)

# code, transition rule
PHASE24_RULE_ROWS: Final = (
    (
        "UNANSWERED_TO_EVIDENCE_PRESENT_UNVERIFIED",
        "A question may leave UNANSWERED only when bounded evidence is present; presence alone does not verify permission.",
    ),
    (
        "INDEPENDENT_VERIFICATION_REQUIRED",
        "No answer becomes verified until identity, authority, exact scope, currentness, and evidence integrity are independently checked.",
    ),
    (
        "ALL_QUESTIONS_REQUIRED",
        "Current-use rights remain blocked unless all ten questions have verified, mutually consistent answers.",
    ),
    (
        "CONDITIONS_MUST_BE_ENFORCEABLE",
        "A conditional permission may pass only after every condition has a fail-closed machine or governance control and acceptance test.",
    ),
    (
        "PROHIBITED_OR_AMBIGUOUS_FAILS_CLOSED",
        "Any prohibited, conflicting, expired, unverified, or ambiguous answer keeps ingestion and operational composition blocked.",
    ),
    (
        "CHANGE_REQUIRES_REVALIDATION",
        "A terms, product, delivery, account, use, rights-holder, or revocation change invalidates prior verification until revalidated.",
    ),
    (
        "PUBLICATION_IS_NOT_AUTHORITY",
        "A commit, pull request, approval, artifact, citation, credential, or generic public research statement cannot substitute for rights evidence.",
    ),
)

PHASE24_ROW_INVARIANTS: Final = MappingProxyType(
    {"external_action_authorized": False, "satisfied": False}
)
PHASE24_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "requirements_only": True,
        "runtime_network_disabled": True,
        "phase23_artifact_unchanged": True,
        "phase23_review_inherited": True,
        "clarification_requirements_frozen": True,
        "provider_contact_performed": False,
        "counsel_contact_performed": False,
        "clarification_request_sent": False,
        "clarification_response_received": False,
        "clarification_evidence_present": False,
        "clarification_verified": False,
        "legal_opinion_obtained": False,
        "rights_granted": False,
        "rights_verified": False,
        "rights_currentness_guaranteed": False,
        "product_selected": False,
        "delivery_selected": False,
        "credentials_loaded": False,
        "account_verified": False,
        "operational_external_request_performed": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
        "data_fitness_review_performed": False,
        "bls_reconciliation_performed": False,
        "operational_source_product_composition_selected": False,
        "research_ingestion_authorized": False,
        "research_executed": False,
        "performance_computed": False,
        "strategy_promotion_authorized": False,
        "execution_authorized": False,
        "order_submission_authorized": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
)
PHASE24_DISCLAIMER: Final = (
    "Rights-clarification requirements only; not outreach, legal advice, a rights grant, entitlement, "
    "product selection, data qualification, research authority, performance, execution authority, "
    "an order, or investment advice."
)


def _policy_payload() -> dict[str, object]:
    return {
        name: value
        for name, value in globals().items()
        if name.startswith("PHASE24_")
        and name
        not in {
            "PHASE24_POLICY_SHA256",
            "PHASE24_ARTIFACT_NAMESPACE",
        }
    } | {"artifact_uuid_namespace": str(PHASE24_ARTIFACT_NAMESPACE)}


PHASE24_POLICY_SHA256: Final = domain_sha256(PHASE24_POLICY_HASH_DOMAIN, _policy_payload())


def identity(policy_sha256: str = PHASE24_POLICY_SHA256) -> UUID:
    return uuid_from_sha256(PHASE24_ARTIFACT_NAMESPACE, policy_sha256)


__all__ = [name for name in globals() if name.startswith("PHASE24_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
