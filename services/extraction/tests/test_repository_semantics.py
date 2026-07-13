from __future__ import annotations

from uuid import UUID

import pytest
from conftest import FIXED_TIME, SOURCE_VERSION_ID, make_source
from fable5_extraction.extractor import default_extraction_profile
from fable5_extraction.models import (
    AuthorityVerificationMethod,
    SourceAuthority,
    SourceIntakeRequest,
    SourceType,
    SourceVersion,
)
from fable5_extraction.repository import (
    IdeaRepository,
    IdempotencyConflictError,
    SourceTextUnavailableError,
)

CORROBORATION_ID = UUID("20000000-0000-0000-0000-000000000099")


def _existing_official_source() -> SourceVersion:
    return make_source(
        "Exact immutable evidence.",
        authority=SourceAuthority.OFFICIAL,
        source_type=SourceType.MANUAL_NOTES,
    )


def test_same_idempotent_payload_ignores_only_server_default_supplied_time() -> None:
    existing = _existing_official_source()
    retry = SourceIntakeRequest(
        source_type=SourceType.MANUAL_NOTES,
        source_authority=SourceAuthority.OFFICIAL,
        raw_text="Exact immutable evidence.",
        ingest_idempotency_key="same-payload-key",
    )

    IdeaRepository._assert_ingest_matches(existing, retry)


@pytest.mark.parametrize(
    "changed",
    [
        {"authority_verification_method": AuthorityVerificationMethod.MANUAL_USER_ATTESTATION},
        {"retrieved_at_utc": FIXED_TIME},
        {"official_corroboration_source_version_ids": [CORROBORATION_ID]},
    ],
    ids=("verification", "content-state", "corroboration"),
)
def test_idempotency_key_rejects_changed_immutable_provenance(
    changed: dict[str, object],
) -> None:
    existing = _existing_official_source()
    retry = SourceIntakeRequest(
        source_type=SourceType.MANUAL_NOTES,
        source_authority=SourceAuthority.OFFICIAL,
        raw_text="Exact immutable evidence.",
        ingest_idempotency_key="changed-provenance-key",
        **changed,
    )

    with pytest.raises(IdempotencyConflictError, match="immutable provenance"):
        IdeaRepository._assert_ingest_matches(existing, retry)


def test_url_only_source_cannot_create_manual_extraction_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = object.__new__(IdeaRepository)
    monkeypatch.setattr(
        repository,
        "get_source_version",
        lambda _source_version_id: make_source(None),
    )

    with pytest.raises(SourceTextUnavailableError, match="URL retrieval is outside Phase 2"):
        repository.create_extraction_request(SOURCE_VERSION_ID, default_extraction_profile())
