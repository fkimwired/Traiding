"""Canonical constants and hash domains for Phase 21 decision requirements."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256
from fable5_data.phase20.canonical import (
    PHASE20_FUTURE_EVIDENCE_ROWS as PHASE20_FUTURE_EVIDENCE_ROWS,
)
from fable5_data.phase20.canonical import (
    PHASE20_GAP_CODES as PHASE20_GAP_CODES,
)
from fable5_data.phase20.canonical import (
    PHASE20_GAP_STATES as PHASE20_GAP_STATES,
)
from fable5_data.phase20.canonical import (
    PHASE20_INPUT_REQUIREMENT_ROWS as PHASE20_INPUT_REQUIREMENT_ROWS,
)
from fable5_data.phase20.canonical import (
    PHASE20_SOURCE_GAP_SHA256S as PHASE20_SOURCE_GAP_SHA256S,
)
from fable5_data.phase20.canonical import (
    PHASE20_STEP_CODES as PHASE20_STEP_CODES,
)
from fable5_data.phase20.canonical import (
    PHASE20_STEP_REASONS as PHASE20_STEP_REASONS,
)
from fable5_data.phase20.canonical import (
    PHASE20_STEP_STATES as PHASE20_STEP_STATES,
)

PHASE21_ARTIFACT_SCHEMA_VERSION: Final = (
    "phase21-family-a-operational-composition-decision-requirements-v1"
)
PHASE21_ARTIFACT_HASH_DOMAIN: Final = PHASE21_ARTIFACT_SCHEMA_VERSION
PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION: Final = "phase21-family-a-candidate-group-binding-v1"
PHASE21_PRODUCT_RIGHTS_SCHEMA_VERSION: Final = "phase21-family-a-product-rights-binding-v1"
PHASE21_CAPABILITY_SCHEMA_VERSION: Final = "phase21-family-a-capability-assignment-v1"
PHASE21_DECISION_FIELD_SCHEMA_VERSION: Final = "phase21-family-a-decision-field-requirement-v1"
PHASE21_DEPENDENCY_SCHEMA_VERSION: Final = "phase21-family-a-post-selection-dependency-v1"
PHASE21_GATE_SCHEMA_VERSION: Final = "phase21-family-a-composition-decision-gate-v1"
PHASE21_RULE_SCHEMA_VERSION: Final = "phase21-family-a-future-composition-rule-v1"
PHASE21_SUBSTITUTE_SCHEMA_VERSION: Final = "phase21-family-a-forbidden-substitute-v1"
PHASE21_INPUT_BINDING_SCHEMA_VERSION: Final = "phase21-family-a-phase20-input-binding-v1"
PHASE21_EVIDENCE_BINDING_SCHEMA_VERSION: Final = "phase21-family-a-prior-evidence-binding-v1"
PHASE21_GAP_BINDING_SCHEMA_VERSION: Final = "phase21-family-a-phase15-gap-binding-v1"
PHASE21_STEP_BINDING_SCHEMA_VERSION: Final = "phase21-family-a-source-plan-step-binding-v1"

PHASE21_CANDIDATE_GROUP_HASH_DOMAIN: Final = PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION
PHASE21_PRODUCT_RIGHTS_HASH_DOMAIN: Final = PHASE21_PRODUCT_RIGHTS_SCHEMA_VERSION
PHASE21_CAPABILITY_HASH_DOMAIN: Final = PHASE21_CAPABILITY_SCHEMA_VERSION
PHASE21_DECISION_FIELD_HASH_DOMAIN: Final = PHASE21_DECISION_FIELD_SCHEMA_VERSION
PHASE21_DEPENDENCY_HASH_DOMAIN: Final = PHASE21_DEPENDENCY_SCHEMA_VERSION
PHASE21_GATE_HASH_DOMAIN: Final = PHASE21_GATE_SCHEMA_VERSION
PHASE21_RULE_HASH_DOMAIN: Final = PHASE21_RULE_SCHEMA_VERSION
PHASE21_SUBSTITUTE_HASH_DOMAIN: Final = PHASE21_SUBSTITUTE_SCHEMA_VERSION
PHASE21_INPUT_BINDING_HASH_DOMAIN: Final = PHASE21_INPUT_BINDING_SCHEMA_VERSION
PHASE21_EVIDENCE_BINDING_HASH_DOMAIN: Final = PHASE21_EVIDENCE_BINDING_SCHEMA_VERSION
PHASE21_GAP_BINDING_HASH_DOMAIN: Final = PHASE21_GAP_BINDING_SCHEMA_VERSION
PHASE21_STEP_BINDING_HASH_DOMAIN: Final = PHASE21_STEP_BINDING_SCHEMA_VERSION

PHASE21_CANDIDATE_GROUPS_MANIFEST_HASH_DOMAIN: Final = "phase21-candidate-groups-manifest-v1"
PHASE21_PRODUCT_RIGHTS_MANIFEST_HASH_DOMAIN: Final = "phase21-product-rights-manifest-v1"
PHASE21_CAPABILITIES_MANIFEST_HASH_DOMAIN: Final = "phase21-capabilities-manifest-v1"
PHASE21_DECISION_FIELDS_MANIFEST_HASH_DOMAIN: Final = "phase21-decision-fields-manifest-v1"
PHASE21_DEPENDENCIES_MANIFEST_HASH_DOMAIN: Final = "phase21-dependencies-manifest-v1"
PHASE21_GATES_MANIFEST_HASH_DOMAIN: Final = "phase21-gates-manifest-v1"
PHASE21_RULES_MANIFEST_HASH_DOMAIN: Final = "phase21-rules-manifest-v1"
PHASE21_SUBSTITUTES_MANIFEST_HASH_DOMAIN: Final = "phase21-substitutes-manifest-v1"
PHASE21_INPUTS_MANIFEST_HASH_DOMAIN: Final = "phase21-phase20-inputs-manifest-v1"
PHASE21_EVIDENCE_MANIFEST_HASH_DOMAIN: Final = "phase21-prior-evidence-manifest-v1"
PHASE21_GAPS_MANIFEST_HASH_DOMAIN: Final = "phase21-phase15-gaps-manifest-v1"
PHASE21_STEPS_MANIFEST_HASH_DOMAIN: Final = "phase21-source-plan-steps-manifest-v1"
PHASE21_POLICY_ID: Final = (
    "phase21-family-a-operational-composition-decision-requirements-policy-v1"
)
PHASE21_POLICY_HASH_DOMAIN: Final = PHASE21_POLICY_ID
PHASE21_ARTIFACT_NAMESPACE: Final = UUID("3ba2670b-a5f2-51a7-a84a-1f02d4f628b6")

PHASE21_ACCEPTED_PHASE20_COMMIT_SHA: Final = "01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a"
PHASE21_ACCEPTED_PHASE20_TREE_SHA: Final = "b7a68998f1c99ed8b19ab08ae8a725726f04c423"
PHASE21_PHASE20_ARTIFACT_ID: Final = "e501d4f8-bebe-5e68-9457-56f6a589f478"
PHASE21_PHASE20_ARTIFACT_SHA256: Final = (
    "902fca99d4fec1943403cbed406259f86c0eee05c41cb835b6daf7d165db340b"
)
PHASE21_PHASE20_POLICY_SHA256: Final = (
    "e6be914218dc8b16b2c019ff8d72338dcf495b7cf375cd95281651b89939a31a"
)
PHASE21_PHASE20_INHERITED_PREREQUISITES_MANIFEST_SHA256: Final = (
    "ee650453fc05597765164b965cd65ee3844b034f51b41b4064a001cda147efe9"
)
PHASE21_PHASE20_INPUTS_MANIFEST_SHA256: Final = (
    "b4ffc11633c0ae41d351b7dd10380c29a47e44f368b9248bc74a412e81c4c0ad"
)
PHASE21_PHASE20_EVIDENCE_MANIFEST_SHA256: Final = (
    "ace85cba35e9ca4ea3a26fe7692591a2d02234b3437e8f2c2763e60aebbdff41"
)
PHASE21_PHASE20_TRANSITION_RULES_MANIFEST_SHA256: Final = (
    "b594a162a1c6124502aa6552634f0d1bba7832bf89e550a2e1f7d21b6f737955"
)
PHASE21_PHASE20_DEPENDENCY_GROUPS_MANIFEST_SHA256: Final = (
    "34b44a2d2995f288947eb7a8da6c21f5fb9c8653316172e3155edaa2b9077379"
)
PHASE21_PHASE20_CONSTRUCTION_GATES_MANIFEST_SHA256: Final = (
    "4e5bad5d5d9441c9e832b6c9511ab8aa9123a4875130b98a2fcdf43c8907692a"
)
PHASE21_PHASE20_FORBIDDEN_SUBSTITUTES_MANIFEST_SHA256: Final = (
    "044b07af06221878b11da497baf8bc838909043f1550cae29669056a84cf4b84"
)
PHASE21_PHASE20_GAPS_MANIFEST_SHA256: Final = (
    "c98b37ca4a0aa8ab9a7641a865f9444e56422be74cadf239c33e3cd3a882334a"
)
PHASE21_PHASE20_STEPS_MANIFEST_SHA256: Final = (
    "e695c826fe23365bf6b89d09626003a8feac3c3aab589266bd56464e5cdaa4bf"
)
PHASE21_PHASE20_AGGREGATE_CONCLUSION: Final = "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS"
PHASE21_PHASE17_ARTIFACT_ID: Final = "19d213d5-ec44-53fc-a146-f4f77a06102d"
PHASE21_PHASE17_ARTIFACT_SHA256: Final = (
    "48584cf614c7713b05417a6d9333ca400f2d1c19fb0d3f047ced42e9ef4eb8f4"
)
PHASE21_PHASE17_POLICY_SHA256: Final = (
    "0a36f01630a40c55d20139117641abcc8313e5f8b5a0be5fce15fd4c8ad2b3cf"
)
PHASE21_PHASE17_PRODUCT_INVENTORY_SHA256: Final = (
    "070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c"
)
PHASE21_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256: Final = (
    "8416991d72e5da5ec83025090e167c2d03a52766fd173be86676f307ec53e623"
)
PHASE21_PHASE17_STEPS_MANIFEST_SHA256: Final = (
    "f762a287ac7488dbe33aed32c220f4ebd0fef66bff685f353f2e798d54d34015"
)
PHASE21_PHASE17_OUTCOME: Final = "BLOCKED"
PHASE21_PHASE18_ARTIFACT_ID: Final = "7008240c-e7a2-5d4b-9345-8c40d2d4c359"
PHASE21_PHASE18_ARTIFACT_SHA256: Final = (
    "2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae"
)
PHASE21_PHASE18_POLICY_SHA256: Final = (
    "e175f9b70333899b8c9626e459f091ea5c440494e006c2684448fa15fe0a4fbb"
)
PHASE21_PHASE18_TERMS_SOURCES_MANIFEST_SHA256: Final = (
    "55d19d4fe8745cf5f0eadd1cbd7b66fd1bd7806fbcb1209a242e1189c21e4bfc"
)
PHASE21_PHASE18_RIGHTS_REVIEW_SHA256: Final = (
    "a0c8808e865931cc88d9f71c578b42edcfb6e279e2426b4b30534d6c4626023b"
)
PHASE21_PHASE18_RIGHTS_CURRENTNESS_SHA256: Final = (
    "91b3b711e3c0b1b3b313e8ea45d9b73f96746ed4bd74478a7f6e7553510cdf63"
)
PHASE21_PHASE18_STEPS_MANIFEST_SHA256: Final = (
    "581ff73113eff3c2d54728106df556734084c053f8e52f0f4a9e6928d7478167"
)
PHASE21_PHASE18_OUTCOME: Final = "BLOCKED"
PHASE21_PHASE18_AGGREGATE_CONCLUSION: Final = "BLOCKED_NO_OPERATIONAL_SELECTION"
PHASE21_PHASE16_ARTIFACT_ID: Final = "e106a766-5cfe-5a1c-94f6-ee1c2ac68652"
PHASE21_PHASE16_ARTIFACT_SHA256: Final = (
    "74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb"
)
PHASE21_PHASE16_POLICY_SHA256: Final = (
    "57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd"
)
PHASE21_PHASE16_REQUIREMENTS_MANIFEST_SHA256: Final = (
    "cc48b8c45112665517c2e525267610b34025aa06a3dc490f27409d569fa72089"
)
PHASE21_PHASE16_CAPABILITIES_MANIFEST_SHA256: Final = (
    "469426253bad297c0db73e152305f97dbaf29126b0ea8c4d49bb047ef1eba47f"
)
PHASE21_PHASE16_CANDIDATES_MANIFEST_SHA256: Final = (
    "75f0197965d8b9c75cba3b292aa4b8e9942896039deb295511c44ab88c837ccd"
)
PHASE21_PHASE16_STEPS_MANIFEST_SHA256: Final = (
    "92e65795b453a63cb1c6b44b4522629226580f90d681caf0032dfd787b94725d"
)
PHASE21_PHASE16_GAP_BINDINGS_MANIFEST_SHA256: Final = (
    "c6df8bcc7d98b682b880484aef028d411f196aaaf414d01949912c969ac9e26d"
)
PHASE21_PHASE16_OUTCOME: Final = "PLAN_FROZEN"

PHASE21_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE21_FROZEN_AT_UTC: Final = "2026-07-20T09:30:00.000000Z"
PHASE21_OUTCOME: Final = "BLOCKED"
PHASE21_REQUIREMENTS_STATE: Final = "DECISION_REQUIREMENTS_FROZEN"
PHASE21_AGGREGATE_CONCLUSION: Final = (
    "BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
)
PHASE21_BLOCK_REASON: Final = (
    "The candidate inventory and public-terms review do not select an operational source, "
    "product, delivery, or capability composition; all eight decision fields are absent and "
    "current account-specific rights remain unverified."
)

# candidate code, product codes, immutable Phase 17 candidate-group hash
PHASE21_CANDIDATE_GROUP_ROWS: Final = (
    (
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        (
            "TIINGO_END_OF_DAY",
            "TIINGO_US_FUNDAMENTALS",
            "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
            "TIINGO_SPLIT_CORPORATE_ACTIONS",
        ),
        "74b443698ea13393559713ef2914fbfac2e7f8034db3d87463724f753b47daa9",
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE",
        ("MORNINGSTAR_CRSP_US_STOCK_DATABASES",),
        "051f6030ef0416cbbd1d331118a142f64213142e0f968f918ac395c2ded22779",
    ),
    (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE",
        ("MORNINGSTAR_CRSP_COMPUSTAT_MERGED",),
        "e33ab114979997360a41c6fd6828ff456528db2ef5aa77beabb1c8f0f0be07ac",
    ),
    (
        "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "4484902b85d39ae3133d78c1ed8fbca51b65865088b180e50f4e0f3077671680",
    ),
    (
        "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
        "75e886a5a7a9ff74a6a9124d84ad5aeb0f3047439d3b5c84801338c664cf2dc7",
    ),
    (
        "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED",
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
        "56dde46957416a536ca9e8c5b234ac4aa0d2fe678ad5974ff6ca599e225ef9b0",
    ),
)

# product code, Phase 17 product hash, Phase 18 rights-finding hash
PHASE21_PRODUCT_RIGHTS_ROWS: Final = (
    (
        "TIINGO_END_OF_DAY",
        "823f95259d3a9132a8c3e8cd58ed850e5a958c9ecf11c3777252a34b772c0bac",
        "19192a3d86681185b97b1ca611b36eda0ace2f1cb796b03d6aabb4de019ea512",
    ),
    (
        "TIINGO_US_FUNDAMENTALS",
        "0c89b810f92394b4b026f85464040280b01aca28126f864fd163d19bcef7cfbe",
        "e7510327f8e329398aba6b2e250e4c8f59a80822e9dde57d3bd2a657438af833",
    ),
    (
        "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
        "6ae798d2ae751ae61b1eff8af98c74ad99896f667d0c45e40827b4d874272356",
        "3412436ecdf97181606294b249eecaea6195ce712d1af50b0e37bab3d2eb186b",
    ),
    (
        "TIINGO_SPLIT_CORPORATE_ACTIONS",
        "17889785e819be747e861513b4abbf5b0618806f16fc88148edab2d2b8127953",
        "fd2e9e7c45774409d0c747b8f03fc2b351980599c18e8c94edcebab6d6b3a59f",
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
        "8105f5bd41edf32701fdaa5c425d067ab0e37ff25d84f2c755971cf21e535fb0",
        "3e0a64c88bc9afb9612c71ac36d5baf1104d526509b4f7ff8d06b2b08be889a8",
    ),
    (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED",
        "0867bcf338a5763d78a1c5acb77b58a829c65b4981bbdf78ccbb1af5ea16c190",
        "ff8131a9c48ca89d1ac43386dcff29c6d5ff407797021513f6209519f121d353",
    ),
    (
        "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
        "13fc0294503de17f2f5661d48b9c74d746cdf148ab8b1509d752770f64972459",
        "cf0b7153819402d8de3e30c8788c46f48a6c676e1c46d5383c0a1f60d9e51301",
    ),
    (
        "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",
        "dce1fbcdf188230ce03862a61b723d7ed63ffab76dc851294c027902de50ffcc",
        "7e286484a11ea083479e3a032d0b74ebbaf76bc0c4061298e746b73a09e2828d",
    ),
    (
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",
        "3f0ea8d981c3b445eff65ea7174acf35aeccde48d42b278494d08eb2f86986a1",
        "0ec96fa0397bd46d5231c886733d3995e3541257ee82f1f62ac4d6032f123762",
    ),
)

PHASE21_CAPABILITY_ROWS: Final = (
    ("security_master", "d49c8548da10521bd8fb3834a31df3941643537ae3f95a733e9759f4893b00b7"),
    ("universe_membership", "9c329b4c82c356a2a956629187f00b8bd7070311332e69aad019a1e9cf9bcf7c"),
    ("ohlcv", "18778079898a0509f7adb64c388f55c0785c82d4d9a2d20d351ad98ffae3b4d6"),
    ("corporate_actions", "932b9776b71b3effaebba604a31c4367fb90da849d9e311ff0826f918cd487e8"),
    ("delistings", "8cb3b081b24f282a17395b5f4d8f1fe359560122edca8933faa02c95450aa7ff"),
    (
        "as_reported_fundamentals",
        "d76cbbf4de9a276dceaa5b3a9b3c796436244f6571fba1bc74a166a4ee1bd9d8",
    ),
    ("macro_regime_inputs", "2ef9b67d7c64e8ae2dfed7f841c4cb8de3b103c3423c452318ae1bda4df47685"),
)

PHASE21_DECISION_FIELD_ROWS: Final = (
    (
        "capability_product_composition_id",
        "Stable identifier for the independently approved capability-to-product composition.",
    ),
    ("source_ids", "Exact ordered operational source identifiers."),
    ("product_ids", "Exact ordered operational product identifiers."),
    ("delivery_ids", "Exact ordered delivery identifiers and variants."),
    ("selection_scope", "Closed operational scope covered by the composition decision."),
    ("selected_at_utc", "UTC time of the separately authorized composition decision."),
    ("selected_by", "Accountable human decision-maker identity."),
    (
        "selection_evidence_sha256",
        "Hash of future independent decision evidence, not supplied by Phase 21.",
    ),
)

PHASE21_POST_SELECTION_DEPENDENCY_ROWS: Final = (
    (
        "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION",
        (
            "Require current account-specific executed rights and revocation status for the "
            "exact composition."
        ),
    ),
    (
        "EXACT_DELIVERY_AND_SCHEMA_VERSIONS",
        "Require exact delivery and schema versions for every selected product.",
    ),
    (
        "DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS",
        (
            "Require point-in-time coverage, calendar, availability, revision, and missingness "
            "contracts."
        ),
    ),
)

PHASE21_GATE_ROWS: Final = (
    (
        "EXPLICIT_HUMAN_COMPOSITION_DECISION",
        "All eight decision fields require a separately authorized accountable human decision.",
    ),
    (
        "SINGLE_CLOSED_COMPOSITION",
        "Exactly one closed capability/source/product/delivery composition must be declared.",
    ),
    (
        "COMPLETE_CAPABILITY_ASSIGNMENT",
        (
            "Every required Phase 16 capability must be explicitly assigned or rejected with "
            "approved rationale."
        ),
    ),
    (
        "CURRENT_RIGHTS_FOR_EXACT_COMPOSITION",
        (
            "Current account-specific rights must cover every exact product, delivery, and "
            "intended use."
        ),
    ),
    (
        "INDEPENDENT_DECISION_EVIDENCE",
        (
            "Independent immutable decision evidence must bind all fields without using a "
            "substitute identity."
        ),
    ),
    (
        "POST_SELECTION_REVALIDATION",
        (
            "All three post-selection dependencies must pass after composition and before any "
            "external action."
        ),
    ),
)

PHASE21_FUTURE_RULE_ROWS: Final = (
    (
        "CANDIDATE_REVIEW_IS_NOT_OPERATIONAL_SELECTION",
        "Phase 17 review naming cannot select a source, product, or delivery.",
    ),
    (
        "RIGHTS_FINDING_IS_NOT_CURRENT_ACCOUNT_RIGHTS",
        "Phase 18 public-terms findings cannot prove current account-specific rights.",
    ),
    (
        "ALL_DECISION_FIELDS_REQUIRED_TOGETHER",
        "No partial decision-field set can create a composition.",
    ),
    (
        "CAPABILITIES_REQUIRE_EXPLICIT_ASSIGNMENT",
        "Every required capability must be assigned within the same closed composition.",
    ),
    (
        "ONE_COMPOSITION_NO_RANKING",
        (
            "A future decision declares one composition and cannot be inferred from a ranking "
            "or score."
        ),
    ),
    (
        "DECISION_EVIDENCE_MUST_BE_INDEPENDENT",
        "Future evidence must be independently produced and hash-bound to the complete decision.",
    ),
    (
        "POST_SELECTION_DEPENDENCIES_RUN_AFTER_DECISION",
        "Rights, schema, and point-in-time coverage checks cannot be pre-satisfied by candidates.",
    ),
    (
        "SEPARATE_AUTHORITY_REQUIRED_FOR_EXTERNAL_ACTION",
        (
            "A completed composition alone grants no provider request, data, research, execution, "
            "or order authority."
        ),
    ),
)

PHASE21_FORBIDDEN_SUBSTITUTE_ROWS: Final = (
    (
        "PHASE17_CANDIDATE_INVENTORY_IDENTITY",
        "A Phase 17 artifact, policy, group, product, or manifest identity.",
    ),
    (
        "PHASE18_RIGHTS_REVIEW_IDENTITY",
        "A Phase 18 artifact, policy, finding, currentness, or manifest identity.",
    ),
    ("PHASE19_ASSESSMENT_IDENTITY", "A Phase 19 assessment identity or prerequisite binding."),
    (
        "PHASE20_INPUT_REGISTER_IDENTITY",
        "A Phase 20 artifact, policy, input, evidence, gap, step, or manifest identity.",
    ),
    ("CANDIDATE_NAME_OR_PUBLIC_URL", "A candidate name, official fact, citation, or public URL."),
    (
        "SCORE_RANK_RECOMMENDATION_OR_DEFAULT",
        "Any score, rank, recommendation, heuristic, fallback, or default.",
    ),
    ("PLACEHOLDER_OR_ALL_ZERO_HASH", "A placeholder, sentinel, all-zero, or arbitrary hash."),
    (
        "OPERATOR_OVERRIDE_OR_SELF_ATTESTATION",
        "An override or unsupported self-attestation without independent evidence.",
    ),
    (
        "PR_TAG_RELEASE_PUBLICATION_DEPLOYMENT_IDENTITY",
        "Any pull-request, tag, release, publication, deployment, workflow, or build identity.",
    ),
    (
        "CREDENTIAL_ACCOUNT_REQUEST_OR_PROVIDER_RESPONSE",
        "Any credential, account identifier, provider request, response, payload, or side effect.",
    ),
)

PHASE21_PHASE20_INPUT_SHA256S: Final = (
    "627d0c39b68e93f642c1f7c23e8e7b3043ec6aef9d043cecb117dec32029afad",
    "4ed420467bbbfd505c10e575ed0b3f0d6774d82e7bf5e23a0d134b969efbd685",
    "7dc7814c24b6f8cc3fedf3791b157d4b30f99edab202aca0eab48642a67360f0",
    "e57d8346ad5723c4d867859192a23391153ab3fd7da4987f468caf695d7fff17",
    "ab8828af40515b30a07caea501b8f57280ad7d6756f2bb48dfe10054a12431f6",
    "b40fff178d9683486a62e449b9627096d59005f6a22e67aed63fca221eb36cd5",
    "71e5be510881efa7ed6c7de880aaa7977b5ab792fc25b397057d81d679e99332",
    "61c89a496856ebfb2aa9ba7a8b4ed7ef1bfb61c4baaff1405491b53aaa3af881",
    "975b7a1d29f754451f6c22deea9a73dfc0cb77374507e1256fa6544a01bb0b54",
    "5dfd73d54c09ea249e9df42dd9ce871f46ee2e72c097a1e21aa5d5cebbffd9fc",
    "993f342500dc30f7f6af33954b49e2ccffa96055ddd46a1d14b26a290ca0a887",
    "5ee9f4b3b66dfca4eb55f56e7f47dfe054ecbb1ef36d751a0fc97cae6f0b04f6",
    "25cae76fd55526a91790175dbc9b689c0323d95980278d5ff09b89c5321b55d3",
    "d2d99da67b7594cd57d3cedac25d5257b7fcc123b2d587d2f2835bb5250d3d15",
    "5e73a95261a54422783eb307a559293607237ba97d240c6c4e7203580bacdde0",
    "92794e187c4ee5398ca65c737a9d32744c874af8a4d81c6948ee003187d94c7e",
    "840b7b675b0081d24a3c4b19ab3d79ef98399c8b14748d907940a7f62f009a55",
    "dc96a2f500a2e4fda28e722bd3622f7d8971b56329a6f73048bb105d44f0ac1b",
    "9c24ce7a0746c7cccd7c27824b106b1297259924945d6f62d5bd69a24373a961",
    "cd44e0e9542d78201dfa98b366a7b05feefec8a95b0aedec33cf2d97413a10b7",
)
PHASE21_PHASE20_EVIDENCE_SHA256S: Final = (
    "aafb66f1b139696bd592b3ec109c64d63fba355893cb295be35efbee61378caa",
    "3ae139ca3aeded468ac94eba7fb027da5a23b4008b44017f9a23cef9f83b8334",
)
PHASE21_PHASE20_GAP_BINDING_SHA256S: Final = (
    "6c1bd0361f26b48b35f8df20891abe438b3e125fe989a7ec06228e3209f42734",
    "09e987980ebb490df608a6dc1742685c3507bd1996fa706db5835497ed368976",
    "e197fb149a427d0dea41c0fe1bc10fe592b47e67b54c9843f9815dc9fd35ab1f",
    "8358808c0a6b813cdade142dd7a064ddde321966b4d9a26f9fd5eb010e690e63",
    "474c340b3ffa652ccfc4da1422753268fb5676c6cd269bcbe63ac892e97bceba",
    "d8cd0e4c8d939729fd5ea7862a3df971e882e33ce8143f58d2414002e2267dd3",
    "506a63d27d5db87e6a8aed44d608f75d55d708ea230895c3f579d7b85aafc0b0",
    "a8a9805a6824344e13f2691429cfe2aa561ee0d738ed7ef9530ee1768ea4877b",
    "9dad844e091d86bc10e43dc72726316a0773ae3d51e63f1e15089c027cf38cbc",
    "8f5faa9d94ac01429582452bfa4b875f48d6e39d6246b8ca6501f0b2b066970b",
    "f448d0da0b09187d2316d85b55bc2c946f3cd3378aa537b492687ca7c482aad5",
    "e38e0ea57497cb5189602476b3a1037c46fc9a0b46668af86a7d604197c1eb85",
    "f66a4b707aa9f8843861867c9757aa4e1b23d168b2903e7473e8982405633d33",
    "e9831f6ee2e13b0460d93079647c2c17e22126d67a65708384d52baf8193d92f",
    "50a60c5561369b5a3d41ba3905357343961b2abb8096392cfab788de3c55b552",
    "67fdff64965f2ed249c1ca242473ae3aa6af6c7ac6ec4d1ce896600472480e41",
    "8344c7620661ce5584b9cfd3b5ee121cc00710ebd3021c937da5ff1d108921a1",
    "69c90ab000aa1d8cf28c680a0dbbd965fe476a07245426fb073e5f736908d3bd",
    "bb5a21f35cb03335a669c7b7f383ab2fe796df14606e9d7b36a1d563fcd364c8",
)
PHASE21_PHASE20_STEP_BINDING_SHA256S: Final = (
    "19c010ba19e5f6bdfd861e7ea056fcad02f9fa4164e63ad40e2024e5f1473565",
    "0a1999db61822fe2cbec9292c41367dd54e45ef9c8d976e238340494adb9d998",
    "644e16cbf04ebb021de2837181e31e5a2acb183a90fa0418eadf3a035067e561",
    "77f4edcc58d539c615b7121030364c24671836de23c155da0c28c262e3da5bd8",
    "ffbefb70a8b0c8287582d47c7d729ac08b98535d9ea24c2c79646b50fb7c84c3",
    "783bfb254f5ba74f536a88c3a0e142249bdd1f6a1f7edd875f0c738fb561a3ae",
    "9695a22e3fc70e0717b8deb93abc2a06043554e23e8a52c5a2fc8d3aee49aa0d",
)

PHASE21_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "requirements_only": True,
        "decision_requirements_only": True,
        "runtime_network_disabled": True,
        "phase20_inputs_unchanged": True,
        "inherited_phase15_gaps_unchanged": True,
        "source_plan_steps_unchanged": True,
        "candidate_groups_candidate_only": True,
        "operational_source_product_composition_selected": False,
        "composition_ranked": False,
        "composition_value_present": False,
        "selection_evidence_produced": False,
        "operational_composition_output_produced": False,
        "provider_selected": False,
        "product_selected": False,
        "source_selected": False,
        "delivery_selected": False,
        "credentials_loaded": False,
        "account_verified": False,
        "rights_currentness_guaranteed": False,
        "rights_verified": False,
        "rights_granted": False,
        "operational_use_cleared": False,
        "operational_external_request_performed": False,
        "provider_data_request_performed": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
        "licensed_data_persisted": False,
        "research_ingestion_authorized": False,
        "research_executed": False,
        "performance_computed": False,
        "execution_authorized": False,
        "order_submission_authorized": False,
        "pull_request_identity_used": False,
        "tag_identity_used": False,
        "release_identity_used": False,
        "publication_identity_used": False,
        "deployment_identity_used": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
)
PHASE21_DISCLAIMER: Final = (
    "Portable decision-requirements evidence only. DECISION_REQUIREMENTS_FROZEN is not an "
    "operational selection, ranking, value, submission, rights grant, provider request, data "
    "capture, research result, execution authority, order, release, publication, or deployment."
)


def _policy_payload() -> dict[str, object]:
    return {
        "policy_id": PHASE21_POLICY_ID,
        "policy_hash_domain": PHASE21_POLICY_HASH_DOMAIN,
        "artifact_uuid_namespace": str(PHASE21_ARTIFACT_NAMESPACE),
        "schemas_and_hash_domains": (
            (PHASE21_ARTIFACT_SCHEMA_VERSION, PHASE21_ARTIFACT_HASH_DOMAIN),
            (PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION, PHASE21_CANDIDATE_GROUP_HASH_DOMAIN),
            (PHASE21_PRODUCT_RIGHTS_SCHEMA_VERSION, PHASE21_PRODUCT_RIGHTS_HASH_DOMAIN),
            (PHASE21_CAPABILITY_SCHEMA_VERSION, PHASE21_CAPABILITY_HASH_DOMAIN),
            (PHASE21_DECISION_FIELD_SCHEMA_VERSION, PHASE21_DECISION_FIELD_HASH_DOMAIN),
            (PHASE21_DEPENDENCY_SCHEMA_VERSION, PHASE21_DEPENDENCY_HASH_DOMAIN),
            (PHASE21_GATE_SCHEMA_VERSION, PHASE21_GATE_HASH_DOMAIN),
            (PHASE21_RULE_SCHEMA_VERSION, PHASE21_RULE_HASH_DOMAIN),
            (PHASE21_SUBSTITUTE_SCHEMA_VERSION, PHASE21_SUBSTITUTE_HASH_DOMAIN),
            (PHASE21_INPUT_BINDING_SCHEMA_VERSION, PHASE21_INPUT_BINDING_HASH_DOMAIN),
            (PHASE21_EVIDENCE_BINDING_SCHEMA_VERSION, PHASE21_EVIDENCE_BINDING_HASH_DOMAIN),
            (PHASE21_GAP_BINDING_SCHEMA_VERSION, PHASE21_GAP_BINDING_HASH_DOMAIN),
            (PHASE21_STEP_BINDING_SCHEMA_VERSION, PHASE21_STEP_BINDING_HASH_DOMAIN),
        ),
        "manifest_hash_domains": (
            PHASE21_CANDIDATE_GROUPS_MANIFEST_HASH_DOMAIN,
            PHASE21_PRODUCT_RIGHTS_MANIFEST_HASH_DOMAIN,
            PHASE21_CAPABILITIES_MANIFEST_HASH_DOMAIN,
            PHASE21_DECISION_FIELDS_MANIFEST_HASH_DOMAIN,
            PHASE21_DEPENDENCIES_MANIFEST_HASH_DOMAIN,
            PHASE21_GATES_MANIFEST_HASH_DOMAIN,
            PHASE21_RULES_MANIFEST_HASH_DOMAIN,
            PHASE21_SUBSTITUTES_MANIFEST_HASH_DOMAIN,
            PHASE21_INPUTS_MANIFEST_HASH_DOMAIN,
            PHASE21_EVIDENCE_MANIFEST_HASH_DOMAIN,
            PHASE21_GAPS_MANIFEST_HASH_DOMAIN,
            PHASE21_STEPS_MANIFEST_HASH_DOMAIN,
        ),
        "accepted_phase20_identity": (
            PHASE21_ACCEPTED_PHASE20_COMMIT_SHA,
            PHASE21_ACCEPTED_PHASE20_TREE_SHA,
            PHASE21_PHASE20_ARTIFACT_ID,
            PHASE21_PHASE20_ARTIFACT_SHA256,
            PHASE21_PHASE20_POLICY_SHA256,
            PHASE21_PHASE20_INHERITED_PREREQUISITES_MANIFEST_SHA256,
            PHASE21_PHASE20_INPUTS_MANIFEST_SHA256,
            PHASE21_PHASE20_EVIDENCE_MANIFEST_SHA256,
            PHASE21_PHASE20_TRANSITION_RULES_MANIFEST_SHA256,
            PHASE21_PHASE20_DEPENDENCY_GROUPS_MANIFEST_SHA256,
            PHASE21_PHASE20_CONSTRUCTION_GATES_MANIFEST_SHA256,
            PHASE21_PHASE20_FORBIDDEN_SUBSTITUTES_MANIFEST_SHA256,
            PHASE21_PHASE20_GAPS_MANIFEST_SHA256,
            PHASE21_PHASE20_STEPS_MANIFEST_SHA256,
            PHASE21_PHASE20_AGGREGATE_CONCLUSION,
        ),
        "phase17_source_identity": (
            PHASE21_PHASE17_ARTIFACT_ID,
            PHASE21_PHASE17_ARTIFACT_SHA256,
            PHASE21_PHASE17_POLICY_SHA256,
            PHASE21_PHASE17_PRODUCT_INVENTORY_SHA256,
            PHASE21_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256,
            PHASE21_PHASE17_STEPS_MANIFEST_SHA256,
            PHASE21_PHASE17_OUTCOME,
        ),
        "phase18_source_identity": (
            PHASE21_PHASE18_ARTIFACT_ID,
            PHASE21_PHASE18_ARTIFACT_SHA256,
            PHASE21_PHASE18_POLICY_SHA256,
            PHASE21_PHASE18_TERMS_SOURCES_MANIFEST_SHA256,
            PHASE21_PHASE18_RIGHTS_REVIEW_SHA256,
            PHASE21_PHASE18_RIGHTS_CURRENTNESS_SHA256,
            PHASE21_PHASE18_STEPS_MANIFEST_SHA256,
            PHASE21_PHASE18_OUTCOME,
            PHASE21_PHASE18_AGGREGATE_CONCLUSION,
        ),
        "phase16_source_identity": (
            PHASE21_PHASE16_ARTIFACT_ID,
            PHASE21_PHASE16_ARTIFACT_SHA256,
            PHASE21_PHASE16_POLICY_SHA256,
            PHASE21_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
            PHASE21_PHASE16_CAPABILITIES_MANIFEST_SHA256,
            PHASE21_PHASE16_CANDIDATES_MANIFEST_SHA256,
            PHASE21_PHASE16_STEPS_MANIFEST_SHA256,
            PHASE21_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
            PHASE21_PHASE16_OUTCOME,
        ),
        "family": PHASE21_FAMILY,
        "frozen_at_utc": PHASE21_FROZEN_AT_UTC,
        "outcome": PHASE21_OUTCOME,
        "requirements_state": PHASE21_REQUIREMENTS_STATE,
        "aggregate_conclusion": PHASE21_AGGREGATE_CONCLUSION,
        "candidate_group_rows": PHASE21_CANDIDATE_GROUP_ROWS,
        "product_rights_rows": PHASE21_PRODUCT_RIGHTS_ROWS,
        "capability_rows": PHASE21_CAPABILITY_ROWS,
        "decision_field_rows": PHASE21_DECISION_FIELD_ROWS,
        "post_selection_dependencies": PHASE21_POST_SELECTION_DEPENDENCY_ROWS,
        "gate_rows": PHASE21_GATE_ROWS,
        "future_rule_rows": PHASE21_FUTURE_RULE_ROWS,
        "forbidden_substitute_rows": PHASE21_FORBIDDEN_SUBSTITUTE_ROWS,
        "phase20_input_rows": PHASE20_INPUT_REQUIREMENT_ROWS,
        "phase20_input_sha256s": PHASE21_PHASE20_INPUT_SHA256S,
        "phase20_evidence_rows": PHASE20_FUTURE_EVIDENCE_ROWS,
        "phase20_evidence_sha256s": PHASE21_PHASE20_EVIDENCE_SHA256S,
        "phase15_gap_codes": PHASE20_GAP_CODES,
        "phase15_gap_states": PHASE20_GAP_STATES,
        "source_gap_sha256s": PHASE20_SOURCE_GAP_SHA256S,
        "phase20_gap_binding_sha256s": PHASE21_PHASE20_GAP_BINDING_SHA256S,
        "step_codes": PHASE20_STEP_CODES,
        "step_states": PHASE20_STEP_STATES,
        "step_reasons": PHASE20_STEP_REASONS,
        "phase20_step_binding_sha256s": PHASE21_PHASE20_STEP_BINDING_SHA256S,
        "boundary_values": dict(PHASE21_BOUNDARY_VALUES),
        "block_reason": PHASE21_BLOCK_REASON,
        "disclaimer": PHASE21_DISCLAIMER,
    }


PHASE21_POLICY_SHA256: Final = domain_sha256(PHASE21_POLICY_HASH_DOMAIN, _policy_payload())


def identity(policy_sha256: str = PHASE21_POLICY_SHA256) -> UUID:
    return uuid_from_sha256(PHASE21_ARTIFACT_NAMESPACE, policy_sha256)
