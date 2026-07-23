# Family A CRSP and RTDSM rights-evidence requirements

## Purpose and boundary

This T-009 document is an operator collection, redaction, and field-mapping checklist for the
completed Phase 27 metadata intake. It is not proof of rights, legal advice, a provider request, an
entitlement, or authority to acquire or use data. It does not replace independent review of the
exact evidence.

The canonical result remains:

```text
outcome: BLOCKED
determination: COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
verified_evidence_recorded: false
```

This package authorizes no provider outreach, network access, credential use, account inspection,
terms acceptance, evidence ingestion, acquisition, schema or point-in-time qualification,
research, strategy, risk change, execution, order, or live capability. The only permitted
execution mode remains paper, and this document creates no execution capability.

## Accepted repository authority

This checklist is derived only from these accepted repository sources:

- [Phase 24 decisions](PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS_DECISIONS.md)
  and the committed Phase 24 requirements artifact, including its ten exact clarification codes;
- [Phase 25 decisions](PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS_DECISIONS.md),
  `services/data/src/fable5_data/phase25/contracts.py`, and the Phase 25 evidence evaluator;
- [Phase 26 decisions](PHASE_26_FAMILY_A_OPERATIONAL_DATA_COMPOSITION_DECISIONS.md) and the
  selected composition `FAMILY_A_CRSP_SEC_RTDSM_V1`; and
- [Phase 27 decisions](PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE_DECISIONS.md),
  `services/data/src/fable5_data/phase27/contracts.py`, and the committed Phase 27 artifact.

These sources define metadata requirements and fail-closed evaluation rules. They do not establish
that any provider has granted the requested rights.

## Common private-authority record

Every CRSP or RTDSM checklist answer that claims `PASS`, `FAIL`, or `CONDITIONAL` must cite one or
more immutable evidence IDs from an independently evaluated private-authority record. The exact
Phase 25 fields are inherited and narrowed by Phase 27's
`SanitizedAuthorityEvidenceInput`:

| Required metadata | Exact Phase 25/27 field |
|---|---|
| Responder organization, stable identity, and role | `authority_evidence[].responder_organization`, `responder_stable_identity`, `responder_role` |
| Verified authority basis and rights-holding entity | `authority_evidence[].authority_basis`, `rights_holding_legal_entity`, `authority_basis_verified` |
| Authenticated responder identity | `authority_evidence[].responder_identity_authenticated` |
| Response, effective, and expiry/currentness dates | `authority_evidence[].response_date_utc`, `effective_date_utc`, `expiry_date_utc`, `expiry_not_applicable_reason` |
| Agreement and terms binding | `authority_evidence[].governing_agreement`, `governing_terms_version` |
| Immutable evidence identity and integrity | `authority_evidence[].immutable_evidence_id`, `immutable_evidence_sha256` |
| Authenticated provenance and locator | `authority_evidence[].authenticated_provenance`, `provenance_locator_sha256` |
| Independent verification | `authority_evidence[].independent_verification_status`, `independent_verifier_identity_sha256` |

Phase 27 requires sanitized codes or hashes for identity and agreement fields. It does not permit
raw names, agreement text, or provider-response bodies in the repository. A valid record requires
`authority_basis` to equal the selected `authenticated_provenance` value plus
`_AUTHORITY_BASIS`, and it requires exactly one of `expiry_date_utc` or
`expiry_not_applicable_reason`.

## CRSP/Morningstar collection and mapping checklist

The selected product is exactly `MORNINGSTAR_CRSP_US_STOCK_DATABASES`; the selected delivery is
exactly `MORNINGSTAR_CRSP_US_STOCK_DATABASES_LINUX_FLAT_FILE`. Every row below must be resolved,
independently verified, and mutually consistent. Each mapping names an existing Phase 27 Pydantic
field; no parallel intake field is defined here.

Each row also requires a matching
`CRSPRightsEntitlementIntake.requirement_answers[]` item whose `RequirementAnswerInput` contains the
listed `code` plus `state`, `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and
`conditions`. `crsp.response_received` must be `true` before any CRSP response metadata is valid,
and each `normalized_value_sha256` must be the Phase 27 normalized-value domain hash of that row's
`normalized_finding`.

| # | Phase 27 requirement and evidence to collect | Exact Phase 27 field mapping |
|---:|---|---|
| 1 | `CRSP_RIGHTS_HOLDER_AND_LICENSEE`: evidence identifying the exact rights-holding legal entity, licensed legal entity, and authority of the applicable signers. Repository metadata must represent identities without personal identifiers. | `crsp.requirement_answers[code=CRSP_RIGHTS_HOLDER_AND_LICENSEE]`; `crsp.licensed_party_identity_sha256`; `crsp.authority_evidence[].rights_holding_legal_entity`; `responder_stable_identity`; `responder_role`; `responder_identity_authenticated`; `authority_basis_verified` |
| 2 | `CRSP_EXECUTED_AGREEMENT`: evidence binding an executed agreement, order form, product schedule, and governing terms version. | `crsp.requirement_answers[code=CRSP_EXECUTED_AGREEMENT]`; `crsp.executed_agreement_sha256`; `crsp.order_form_or_product_schedule_sha256`; `crsp.authority_evidence[].governing_agreement`; `governing_terms_version` |
| 3 | `CRSP_PRODUCT_AND_SKU`: evidence binding the entitlement to the exact selected product and SKU, not a generic product catalog. | `crsp.requirement_answers[code=CRSP_PRODUCT_AND_SKU]`; `crsp.product_code`; `crsp.product_sku_sha256` |
| 4 | `CRSP_LINUX_FLAT_FILE_ENTITLEMENT`: evidence proving entitlement to the exact selected Linux flat-file delivery, not merely its availability as an option. | `crsp.requirement_answers[code=CRSP_LINUX_FLAT_FILE_ENTITLEMENT]`; `crsp.delivery_id` |
| 5 | `CRSP_CAPABILITY_SCOPE`: evidence covering security master, historical universe membership, OHLCV, corporate actions, and delistings for the selected composition. | `crsp.requirement_answers[code=CRSP_CAPABILITY_SCOPE]`; `crsp.selected_capability_codes` |
| 6 | `CRSP_TERRITORY_USERS_DEVICES`: evidence stating territory, every permitted user, and device or installation limits. | `crsp.requirement_answers[code=CRSP_TERRITORY_USERS_DEVICES]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 7 | `CRSP_ENVIRONMENTS`: evidence covering local development, test, internal research, backtest, and clearly simulated paper environments. | `crsp.requirement_answers[code=CRSP_ENVIRONMENTS]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 8 | `CRSP_AUTOMATED_ACCESS_AND_LOAD`: evidence stating delivery, installation, update, frequency, concurrency, rate, and bulk-access constraints. | `crsp.requirement_answers[code=CRSP_AUTOMATED_ACCESS_AND_LOAD]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 9 | `CRSP_EXACT_BYTES_AND_SNAPSHOT_STORAGE`: evidence separately resolving exact delivery-byte storage, immutable point-in-time snapshots, and reproducibility copies. | `crsp.requirement_answers[code=CRSP_EXACT_BYTES_AND_SNAPSHOT_STORAGE]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 10 | `CRSP_BACKUPS_RETENTION_DELETION`: evidence stating backup handling, retention limits, deletion deadlines, and post-termination obligations. | `crsp.requirement_answers[code=CRSP_BACKUPS_RETENTION_DELETION]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 11 | `CRSP_NORMALIZATION_AND_POINT_IN_TIME`: evidence resolving normalization, identifier history, adjustments, revisions, and point-in-time transformations. | `crsp.requirement_answers[code=CRSP_NORMALIZATION_AND_POINT_IN_TIME]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 12 | `CRSP_NONDISPLAY_INTERNAL_RESEARCH`: evidence resolving internal/non-display feature generation, statistical modeling, backtesting, and simulated paper research. | `crsp.requirement_answers[code=CRSP_NONDISPLAY_INTERNAL_RESEARCH]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 13 | `CRSP_DERIVED_ARTIFACTS`: evidence resolving derived features, aggregates, diagnostics, model parameters, and audit hashes. | `crsp.requirement_answers[code=CRSP_DERIVED_ARTIFACTS]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 14 | `CRSP_DISPLAY_EXPORT_SHARING_REDISTRIBUTION`: evidence separately resolving display, export, internal sharing, publication, and redistribution for raw and derived outputs. | `crsp.requirement_answers[code=CRSP_DISPLAY_EXPORT_SHARING_REDISTRIBUTION]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 15 | `CRSP_ATTRIBUTION_AND_NOTICES`: evidence stating required labels, notices, citations, attribution, and permitted use of names or marks. | `crsp.requirement_answers[code=CRSP_ATTRIBUTION_AND_NOTICES]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 16 | `CRSP_THIRD_PARTY_RIGHTS`: evidence establishing applicable exchange, contributor, and other upstream rights for the exact fields and uses. | `crsp.requirement_answers[code=CRSP_THIRD_PARTY_RIGHTS]`; `crsp.third_party_rights_evidence_ids` |
| 17 | `CRSP_AUDIT_AND_COMPLIANCE`: evidence stating audit, reporting, usage-measurement, and compliance-control obligations. | `crsp.requirement_answers[code=CRSP_AUDIT_AND_COMPLIANCE]` and its `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions` |
| 18 | `CRSP_TERMINATION_REVOCATION_CURRENTNESS`: evidence stating term, renewal, change notice, suspension, revocation, cure, cessation, expiry, and revalidation requirements. | `crsp.requirement_answers[code=CRSP_TERMINATION_REVOCATION_CURRENTNESS]`; `crsp.authority_evidence[].response_date_utc`; `effective_date_utc`; `expiry_date_utc`; `expiry_not_applicable_reason`; `governing_terms_version` |

The CRSP aggregate additionally requires all 18 rows satisfied; all authority records independently
verified and current at `Phase27EvidenceIntake.evaluated_at_utc`; and exact, nonempty values for
`licensed_party_identity_sha256`, `executed_agreement_sha256`,
`order_form_or_product_schedule_sha256`, `product_code`, `product_sku_sha256`, `delivery_id`,
`selected_capability_codes`, and `third_party_rights_evidence_ids`. The product, delivery, and
capability values must equal the closed Phase 26 selection, and every third-party evidence ID must
resolve to current, verified authority evidence.

The aggregate also requires `crsp.mutual_consistency_status=VERIFIED` and nonempty
`crsp.mutual_consistency_evidence_ids` that reference independently verified CRSP authority
records. A row-level answer does not bypass any aggregate gate.

## RTDSM authenticated exact-scope response checklist

All ten Phase 24 questions must receive an explicit, product-specific `PASS`, `FAIL`, or controlled
`CONDITIONAL` answer backed by independently verified evidence. A claimed non-missing answer without
verified evidence is reduced to `MISSING`. Every controlled condition must use the existing
`condition_id`, `control_id`, `acceptance_test_id`, `enforceable`, and
`acceptance_test_passed` fields.

For every row, the common answer mapping is
`Phase27EvidenceIntake.rtdsm.question_answers[]`, using the inherited Phase 25
`QuestionAnswerInput` fields `code`, `state`, `normalized_finding`, `evidence_ids`, and `conditions`.
The exact-scope mappings are
`Phase27EvidenceIntake.rtdsm.scope_answers[]`, using `ScopeAnswerInput.code`, `state`,
`normalized_determination`, `normalized_value_sha256`, `evidence_ids`, and `conditions`.
`rtdsm.response_received` must be `true` before any RTDSM response metadata is valid. Except for
`ACCOUNT_OR_ENTITLEMENT`, each scope row's `normalized_value_sha256` must be the Phase 25
normalized-value domain hash of `normalized_determination`; the account/entitlement SHA-256 must
instead be a distinct hash-only identity.

The scope entries associated with each question below are an operator coverage crosswalk. The
Pydantic contracts keep the question and scope registries independent and do not create a
question-to-scope linkage. The exact field paths remain authoritative, and all nineteen scope rows
must be evaluated independently.

| # | Exact Phase 24 code and question | Authenticated exact-scope response required | Operator crosswalk to exact Phase 24/25/27 fields |
|---:|---|---|---|
| 1 | `PERSISTENT_STORAGE`: May Fable5 persist exact RTDSM delivery bytes and normalized point-in-time snapshots, including reproducibility copies and backups? | Explicitly resolve raw bytes, immutable snapshots, normalization/PIT transformations, backups, and reproducibility copies. | Phase 24 `clarification_questions[code=PERSISTENT_STORAGE].phase23_rights_field=persistent_storage`; `rtdsm.question_answers[code=PERSISTENT_STORAGE]`; `rtdsm.scope_answers[code=RAW_PAYLOAD_STORAGE]`; `rtdsm.scope_answers[code=IMMUTABLE_SNAPSHOT_STORAGE]`; `rtdsm.scope_answers[code=NORMALIZATION_AND_POINT_IN_TIME]`; `rtdsm.scope_answers[code=BACKUPS_AND_REPRODUCIBILITY]` |
| 2 | `AUTOMATED_MODEL_INTERNAL_USE`: May Fable5 use RTDSM data in automated internal feature generation, statistical modeling, backtesting, and simulated paper-trading research? | Explicitly resolve each internal use and the local-development, test, and simulated-paper environments. | Phase 24 `clarification_questions[code=AUTOMATED_MODEL_INTERNAL_USE].phase23_rights_field=automated_model_internal_use`; `rtdsm.question_answers[code=AUTOMATED_MODEL_INTERNAL_USE]`; `rtdsm.scope_answers[code=ENVIRONMENTS]`; `rtdsm.scope_answers[code=INTERNAL_RESEARCH_USES]` |
| 3 | `DERIVED_DATA_AND_MODEL_ARTIFACTS`: May Fable5 retain and use derived features, aggregates, diagnostics, model parameters, and audit hashes after processing RTDSM data? | Explicitly resolve each listed derived artifact and its permitted retention/use. | Phase 24 `clarification_questions[code=DERIVED_DATA_AND_MODEL_ARTIFACTS].phase23_rights_field=derived_data`; `rtdsm.question_answers[code=DERIVED_DATA_AND_MODEL_ARTIFACTS]`; `rtdsm.scope_answers[code=DERIVED_ARTIFACTS]` |
| 4 | `RETENTION_DELETION`: What retention limits, deletion deadlines, backup handling, and post-termination obligations apply to raw and derived artifacts? | State exact retention, deletion, termination, and backup/reproducibility obligations. | Phase 24 `clarification_questions[code=RETENTION_DELETION].phase23_rights_field=retention_deletion`; `rtdsm.question_answers[code=RETENTION_DELETION]`; `rtdsm.scope_answers[code=RETENTION_DELETION_TERMINATION]`; `rtdsm.scope_answers[code=BACKUPS_AND_REPRODUCIBILITY]` |
| 5 | `REDISTRIBUTION_AND_DISPLAY`: What internal sharing, user display, export, publication, and redistribution restrictions apply to raw values and derived outputs? | Resolve display, export, sharing, publication, and redistribution separately for raw and derived outputs. | Phase 24 `clarification_questions[code=REDISTRIBUTION_AND_DISPLAY].phase23_rights_field=redistribution`; `rtdsm.question_answers[code=REDISTRIBUTION_AND_DISPLAY]`; `rtdsm.scope_answers[code=DISPLAY_EXPORT_SHARING_PUBLICATION_REDISTRIBUTION]` |
| 6 | `ATTRIBUTION`: What source labels, notices, citations, or attribution text are required for stored data and derived outputs? | State the required labels, notices, citations, and attribution for the exact product and outputs. | Phase 24 `clarification_questions[code=ATTRIBUTION].phase23_rights_field=attribution`; `rtdsm.question_answers[code=ATTRIBUTION]`; `rtdsm.scope_answers[code=ATTRIBUTION]` |
| 7 | `THIRD_PARTY_BLS_CONTENT`: Does the permission cover BLS-originated PCPI content for the exact proposed uses, or is separate rights-holder permission required? | Explicitly resolve BLS-originated PCPI coverage; a positive Phase 27 scope determination must be `PCPI_BLS_ORIGIN_EXPLICITLY_COVERED`. | Phase 24 `clarification_questions[code=THIRD_PARTY_BLS_CONTENT].phase23_rights_field=third_party_content`; `rtdsm.question_answers[code=THIRD_PARTY_BLS_CONTENT]`; `rtdsm.scope_answers[code=PCPI_AND_BLS_ORIGIN]` |
| 8 | `AUTOMATED_ACCESS_AND_LOAD`: Which delivery method, automated access pattern, frequency, concurrency, and rate or bulk-download limits are authorized? | Bind the response to the selected workbook delivery and state all automated-access limits. | Phase 24 `clarification_questions[code=AUTOMATED_ACCESS_AND_LOAD].phase23_rights_field=access_load`; `rtdsm.question_answers[code=AUTOMATED_ACCESS_AND_LOAD]`; `rtdsm.scope_answers[code=DELIVERY_METHOD_AND_SURFACE]`; `rtdsm.scope_answers[code=AUTOMATED_ACCESS_LIMITS]` |
| 9 | `REVOCATION_AND_CURRENTNESS`: What effective date, term version, change notice, revocation trigger, cure period, and revalidation cadence govern the permission? | State effective/current terms, expiry or no-expiry basis, change notice, revocation, cessation, and revalidation cadence. | Phase 24 `clarification_questions[code=REVOCATION_AND_CURRENTNESS].phase23_rights_field=revocation_currentness`; `rtdsm.question_answers[code=REVOCATION_AND_CURRENTNESS]`; `rtdsm.scope_answers[code=REVOCATION_AND_REVALIDATION]`; `rtdsm.authority_evidence[].effective_date_utc`, `expiry_date_utc`, `expiry_not_applicable_reason`, `governing_terms_version` |
| 10 | `AUTHORITY_AND_PRODUCT_SCOPE`: Which rights-holding entity and authorized representative can bind the exact product, series, delivery, account, users, and proposed use? | Authenticate authority and bind the exact RTDSM product, `PCPI`, selected workbook delivery, individual licensed party, hash-only account/entitlement identity, and every user/device. | Phase 24 `clarification_questions[code=AUTHORITY_AND_PRODUCT_SCOPE].phase23_rights_field=operational_use_cleared`; `rtdsm.question_answers[code=AUTHORITY_AND_PRODUCT_SCOPE]`; `rtdsm.scope_answers[code=PRODUCT]`; `rtdsm.scope_answers[code=REQUESTED_SERIES]`; `rtdsm.scope_answers[code=DELIVERY_METHOD_AND_SURFACE]`; `rtdsm.scope_answers[code=LICENSED_PARTY]`; `rtdsm.scope_answers[code=ACCOUNT_OR_ENTITLEMENT]`; `rtdsm.scope_answers[code=PERMITTED_USERS_AND_DEVICES]`; `rtdsm.authority_evidence[]` |

For a positive exact-scope evaluation, Phase 27 requires:

- `PRODUCT` to bind `PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS` (translated only in
  memory for the accepted Phase 25 evaluator);
- `REQUESTED_SERIES` to bind `PCPI`;
- `DELIVERY_METHOD_AND_SURFACE` to bind
  `PHILADELPHIA_FED_RTDSM_PCPI_MONTHLY_VINTAGE_WORKBOOK`;
- `LICENSED_PARTY` to bind `INDIVIDUAL_ACCOUNT_HOLDER`;
- `ACCOUNT_OR_ENTITLEMENT` to use `normalized_determination=SANITIZED_HASH_ONLY` and a distinct
  `normalized_value_sha256`; and
- `rtdsm.mutual_consistency_status=VERIFIED` with nonempty
  `rtdsm.mutual_consistency_evidence_ids` that reference independently verified authority records.

Every one of the ten question codes and all nineteen exact-scope codes must satisfy. All RTDSM
authority records must be independently verified and current at
`Phase27EvidenceIntake.evaluated_at_utc`, and the exact selected scope must bind. One favorable
answer cannot substitute for another missing scope row.

## Acceptable Phase 25 evidence forms and authority

`AuthorityEvidenceInput.authenticated_provenance` accepts exactly these Phase 25 forms:

| Evidence form | Recordable by the Pydantic contract | Can make `authority_verified=true` |
|---|---:|---:|
| `EXECUTED_AGREEMENT` | Yes | Only when the four record-level verification gates below pass |
| `AUTHENTICATED_PROVIDER_PORTAL` | Yes | Only when the four record-level verification gates below pass |
| `CRYPTOGRAPHICALLY_SIGNED_RESPONSE` | Yes | Only when the four record-level verification gates below pass |
| `RIGHTS_HOLDER_RECORD` | Yes | Only when the four record-level verification gates below pass |
| `EMAIL_ONLY` | Yes | No |
| `PUBLIC_WEBPAGE_ONLY` | Yes | No |
| `VERBAL_STATEMENT` | Yes | No |
| `SCREENSHOT_ONLY` | Yes | No |

Forms such as `EMAIL_ONLY` may therefore be recorded when permitted by the Pydantic contract, but a
recordable form does not automatically become verified authority. Even a potentially verifiable
form produces `authority_verified=true` only when:

- `independent_verification_status=VERIFIED`;
- `responder_identity_authenticated=true`;
- `authority_basis_verified=true`; and
- the form is one of the four verifiable provenance values above.

Scope satisfaction, evidence currentness, exact selected-scope binding, and mutual consistency are
separate aggregate gates; they are not part of the record-level `authority_verified` formula.

Every question, scope, or CRSP requirement claiming a non-missing state must cite qualifying
`immutable_evidence_id` values through its existing `evidence_ids` field. The aggregate must also
record the applicable `mutual_consistency_status` and verified
`mutual_consistency_evidence_ids`. Evidence presence alone is not verification.

## Phase 26 post-selection evidence dependencies

The Phase 26 dependency `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION` remains blocked. Its three
provider-specific evidence components are:

| Dependency | Exact Phase 26/27 binding | T-009 treatment |
|---|---|---|
| Current executed CRSP rights plus exact Linux delivery entitlement | Phase 26 `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION`; Phase 27 `crsp`, including `CRSP_EXECUTED_AGREEMENT` and `CRSP_LINUX_FLAT_FILE_ENTITLEMENT` | Covered by the CRSP checklist; no evidence is supplied or verified here |
| Authenticated RTDSM exact-scope response | Phase 26 `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION`; Phase 27 `rtdsm`; Phase 25 ten questions and nineteen scope rows | Covered by the RTDSM checklist; no response is supplied or verified here |
| Current first-party SEC EDGAR policy evidence | Phase 26 `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION`; Phase 27 `sec` | Identified only as a required dependency. The separately scoped T-007 SEC policy/schema plan is not part of T-009 |

Phase 26's `EXACT_DELIVERY_AND_SCHEMA_VERSIONS` and
`DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS` dependencies also remain blocked and
separate. Rights metadata does not satisfy either one.

Even if every provider-level evidence group later passes, the Phase 27 package additionally
requires `Phase27EvidenceIntake.composition_consistency_status=VERIFIED` and nonempty
`composition_consistency_evidence_ids`. Those IDs must resolve to current, independently verified
evidence and represent the CRSP, SEC, and RTDSM groups. T-009 supplies none of those records.

## Redaction and repository handling

Do not store any of the following in this repository, including Markdown, fixtures, test output,
logs, artifacts, generated contracts, commits, or CI output:

- raw agreements, order forms, product schedules, or terms text;
- provider emails, portal pages, response bodies, headers, or attachments;
- personal names, signatures, email addresses, phone numbers, or other personal identifiers;
- credentials, passwords, API keys, cookies, account numbers, entitlement tokens, or session data;
- raw provider data, exact delivery bytes, downloaded files, or schema samples; or
- unredacted verifier identity or evidence-location details.

Repository intake is limited to the exact sanitized metadata permitted by Phase 27: normalized
codes, SHA-256 values, immutable evidence IDs, UTC dates, closed evaluation states, enforceable
condition/control/test IDs, authenticated-provenance metadata, and independent-verification-status
metadata. Raw agreements map only to hashes such as `governing_agreement`,
`executed_agreement_sha256`, or
`order_form_or_product_schedule_sha256`. Account or entitlement identity maps only to
`SANITIZED_HASH_ONLY` plus a distinct SHA-256.

This checklist does not define where a human should custody source evidence and is not a
send-ready provider communication.

## Fail-closed operator decision table

| Observed evidence state | Required result | Authority consequence |
|---|---|---|
| Missing response, record, question, requirement, scope row, or evidence reference | `BLOCKED` / missing | No rights or entitlement is established |
| Incomplete evidence or uncontrolled `CONDITIONAL` answer | `BLOCKED` | No checklist item is promoted |
| Stale, expired, superseded, or not yet effective evidence | `BLOCKED` | Historical metadata cannot establish currentness |
| Unverifiable provenance, unauthenticated identity, or unverified authority basis | `BLOCKED` | A recordable item is not verified authority |
| Product, SKU, series, delivery, party, account, user, territory, environment, use, or terms mismatch | `BLOCKED` | Generic or adjacent rights cannot satisfy exact scope |
| Structurally accepted metadata | Remains `BLOCKED` unless every substantive and aggregate gate independently passes | Schema validity does not prove rights |
| Every substantive row satisfied, exact scope bound, evidence current, and authority and mutual consistency independently verified | `BLOCKED / VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY` | Records evidence only; grants no acquisition authority |
| Any Phase 27 rights outcome | Stop before Phase 28 | Grants no schema, PIT, research, strategy, risk, execution, order, or live authority |

The following negative assertions are literal requirements:

- Public research language is not rights evidence.
- An API key is not rights evidence.
- Successful retrieval is not rights evidence.
- An open-source client library is not data-use authorization.
- Free access is not evidence of storage, derived-use, retention, or redistribution rights.
- Credential fields are rejected by the Phase 27 intake.
- Provider URL fetching and all network access are absent.
- Raw provider bodies, agreements, personal identifiers, tokens, data files, and schema samples are
  rejected.
- Research and candidate-screen output are absent.
- Strategy, performance, risk-promotion, order, execution, cancellation, liquidation, and
  live-capable surfaces are absent.
- The only permitted execution mode remains paper.
- A passing metadata record creates no provider-evidence or external-data authority.

## Operator completion check and stop condition

Before treating any later, separately authorized evidence intake as complete or relying on its
classification, confirm:

- all 18 CRSP requirement codes have exact field mappings and independently verified evidence;
- all ten exact Phase 24 question codes and all nineteen Phase 25 scope codes have exact field
  mappings and independently verified evidence;
- the three provider-specific Phase 26 rights-dependency components are complete, current, and
  mutually consistent;
- only permitted sanitized metadata would enter a Phase 27 intake; and
- no passing metadata record is treated as acquisition, qualification, research, strategy, risk,
  execution, order, or live authority.

Stop after this document. Provider outreach, evidence custody, evidence acquisition, and evidence
verification remain human actions outside T-009. T-007, T-010, Phase 28, provider acquisition, and
any future paper-only execution work require separate authorization. Live capability remains
categorically prohibited.
