from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import IntegrityError

from fable5_extraction.extractor import ExtractionDraft, extraction_fingerprint
from fable5_extraction.models import (
    CardWithMemo,
    ContentState,
    ExtractionEventType,
    ExtractionProfile,
    ExtractionRequestRecord,
    ResearchMemo,
    SourceCorrectionRequest,
    SourceCreateResponse,
    SourceDetailResponse,
    SourceIntakeRequest,
    SourceRecord,
    SourceVersion,
    TradingIdeaCard,
)


class NotFoundError(LookupError):
    pass


class InvalidCorroborationError(ValueError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class SourceTextUnavailableError(ValueError):
    pass


def _content_state(request: SourceIntakeRequest) -> ContentState:
    if request.raw_text is None:
        return ContentState.URL_ONLY_UNRETRIEVED
    if request.retrieved_at_utc is not None:
        return ContentState.RETRIEVED_TEXT
    return ContentState.SUPPLIED_TEXT


def _content_bytes(raw_text: str | None) -> bytes:
    return b"" if raw_text is None else raw_text.encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(rendered.encode("utf-8"))


def _bytes(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytes):
        return value
    raise TypeError("unexpected binary database value")


class IdeaRepository:
    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if engine is None and database_url is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _source_from_row(row: RowMapping) -> SourceRecord:
        return SourceRecord(source_id=row["id"], created_at_utc=row["created_at_utc"])

    def _corroboration_ids(self, connection: Connection, source_version_id: UUID) -> list[UUID]:
        rows = connection.execute(
            text(
                "SELECT official_source_version_id "
                "FROM research_source_version_corroborations "
                "WHERE source_version_id = :source_version_id "
                "ORDER BY official_source_version_id"
            ),
            {"source_version_id": source_version_id},
        ).scalars()
        return list(rows)

    def _version_from_row(self, connection: Connection, row: RowMapping) -> SourceVersion:
        raw_content = _bytes(row["raw_content"])
        raw_text = raw_content.decode("utf-8") if raw_content is not None else None
        return SourceVersion(
            source_version_id=row["id"],
            source_id=row["source_id"],
            source_version=row["version_number"],
            parent_source_version_id=row["parent_source_version_id"],
            source_type=row["source_type"],
            source_authority=row["source_authority"],
            source_url=row["source_url"],
            content_state=row["content_state"],
            raw_text=raw_text,
            content_sha256=row["content_sha256"],
            supplied_at_utc=row["supplied_at_utc"],
            retrieved_at_utc=row["retrieved_at_utc"],
            authority_verification_method=row["authority_verification_method"],
            official_corroboration_source_version_ids=self._corroboration_ids(
                connection, row["id"]
            ),
            created_at_utc=row["created_at_utc"],
        )

    def _load_version(self, connection: Connection, source_version_id: UUID) -> SourceVersion:
        row = (
            connection.execute(
                text("SELECT * FROM research_source_versions WHERE id = :id"),
                {"id": source_version_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise NotFoundError(f"source version {source_version_id} was not found")
        return self._version_from_row(connection, row)

    def _load_source(self, connection: Connection, source_id: UUID) -> SourceRecord:
        row = (
            connection.execute(
                text("SELECT * FROM research_sources WHERE id = :id"), {"id": source_id}
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise NotFoundError(f"source {source_id} was not found")
        return self._source_from_row(row)

    def _existing_ingest(
        self, connection: Connection, ingest_idempotency_key: str | None
    ) -> SourceVersion | None:
        if ingest_idempotency_key is None:
            return None
        row = (
            connection.execute(
                text("SELECT * FROM research_source_versions WHERE ingest_idempotency_key = :key"),
                {"key": ingest_idempotency_key},
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else self._version_from_row(connection, row)

    @staticmethod
    def _assert_ingest_matches(existing: SourceVersion, request: SourceIntakeRequest) -> None:
        expected_hash = _sha256(_content_bytes(request.raw_text))
        if (
            existing.content_sha256 != expected_hash
            or existing.source_type is not request.source_type
            or existing.source_authority is not request.source_authority
            or existing.source_url != request.source_url
            or existing.content_state is not _content_state(request)
            or existing.retrieved_at_utc != request.retrieved_at_utc
            or existing.authority_verification_method is not request.authority_verification_method
            or set(existing.official_corroboration_source_version_ids)
            != set(request.official_corroboration_source_version_ids)
        ):
            raise IdempotencyConflictError(
                "ingest idempotency key was already used for different immutable provenance"
            )

    def _validate_and_insert_corroborations(
        self,
        connection: Connection,
        source_version_id: UUID,
        official_version_ids: list[UUID],
    ) -> None:
        for official_version_id in dict.fromkeys(official_version_ids):
            row = (
                connection.execute(
                    text("SELECT source_authority FROM research_source_versions WHERE id = :id"),
                    {"id": official_version_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None or row["source_authority"] != "official":
                raise InvalidCorroborationError(
                    "corroboration must reference an immutable official source version"
                )
            connection.execute(
                text(
                    "INSERT INTO research_source_version_corroborations "
                    "(source_version_id, official_source_version_id) "
                    "VALUES (:source_version_id, :official_source_version_id)"
                ),
                {
                    "source_version_id": source_version_id,
                    "official_source_version_id": official_version_id,
                },
            )

    def _insert_version(
        self,
        connection: Connection,
        *,
        source_id: UUID,
        version_number: int,
        parent_source_version_id: UUID | None,
        request: SourceIntakeRequest,
    ) -> SourceVersion:
        source_version_id = uuid4()
        raw_content = None if request.raw_text is None else request.raw_text.encode("utf-8")
        content_sha256 = _sha256(_content_bytes(request.raw_text))
        ingest_key = request.ingest_idempotency_key or f"generated-{uuid4()}"
        row = (
            connection.execute(
                text(
                    """
                INSERT INTO research_source_versions (
                    id, source_id, version_number, parent_source_version_id,
                    source_type, source_authority, source_url, content_state,
                    raw_content, content_sha256, retrieved_at_utc,
                    authority_verification_method, ingest_idempotency_key
                ) VALUES (
                    :id, :source_id, :version_number, :parent_source_version_id,
                    :source_type, :source_authority, :source_url, :content_state,
                    :raw_content, :content_sha256, :retrieved_at_utc,
                    :authority_verification_method, :ingest_idempotency_key
                ) RETURNING *
                """
                ),
                {
                    "id": source_version_id,
                    "source_id": source_id,
                    "version_number": version_number,
                    "parent_source_version_id": parent_source_version_id,
                    "source_type": request.source_type.value,
                    "source_authority": request.source_authority.value,
                    "source_url": request.source_url,
                    "content_state": _content_state(request).value,
                    "raw_content": raw_content,
                    "content_sha256": content_sha256,
                    "retrieved_at_utc": request.retrieved_at_utc,
                    "authority_verification_method": (
                        None
                        if request.authority_verification_method is None
                        else request.authority_verification_method.value
                    ),
                    "ingest_idempotency_key": ingest_key,
                },
            )
            .mappings()
            .one()
        )
        self._validate_and_insert_corroborations(
            connection,
            source_version_id,
            request.official_corroboration_source_version_ids,
        )
        return self._version_from_row(connection, row)

    def create_source(self, request: SourceIntakeRequest) -> tuple[SourceRecord, SourceVersion]:
        try:
            with self.engine.begin() as connection:
                existing = self._existing_ingest(connection, request.ingest_idempotency_key)
                if existing is not None:
                    self._assert_ingest_matches(existing, request)
                    return self._load_source(connection, existing.source_id), existing
                source_id = uuid4()
                source_row = (
                    connection.execute(
                        text("INSERT INTO research_sources (id) VALUES (:id) RETURNING *"),
                        {"id": source_id},
                    )
                    .mappings()
                    .one()
                )
                version = self._insert_version(
                    connection,
                    source_id=source_id,
                    version_number=1,
                    parent_source_version_id=None,
                    request=request,
                )
                return self._source_from_row(source_row), version
        except IntegrityError:
            if request.ingest_idempotency_key is None:
                raise
            with self.engine.connect() as connection:
                existing = self._existing_ingest(connection, request.ingest_idempotency_key)
                if existing is None:
                    raise
                self._assert_ingest_matches(existing, request)
                return self._load_source(connection, existing.source_id), existing

    def add_source_version(
        self, source_id: UUID, request: SourceCorrectionRequest
    ) -> SourceVersion:
        with self.engine.begin() as connection:
            locked_source = connection.execute(
                text("SELECT id FROM research_sources WHERE id = :id FOR UPDATE"),
                {"id": source_id},
            ).one_or_none()
            if locked_source is None:
                raise NotFoundError(f"source {source_id} was not found")
            existing = self._existing_ingest(connection, request.ingest_idempotency_key)
            if existing is not None:
                if existing.source_id != source_id:
                    raise IdempotencyConflictError(
                        "ingest idempotency key belongs to another source"
                    )
                self._assert_ingest_matches(existing, request)
                return existing
            prior = (
                connection.execute(
                    text(
                        "SELECT * FROM research_source_versions "
                        "WHERE source_id = :source_id ORDER BY version_number DESC LIMIT 1"
                    ),
                    {"source_id": source_id},
                )
                .mappings()
                .one()
            )
            return self._insert_version(
                connection,
                source_id=source_id,
                version_number=int(prior["version_number"]) + 1,
                parent_source_version_id=prior["id"],
                request=request,
            )

    def get_source(self, source_id: UUID) -> SourceDetailResponse:
        with self.engine.connect() as connection:
            source = self._load_source(connection, source_id)
            rows = connection.execute(
                text(
                    "SELECT * FROM research_source_versions WHERE source_id = :source_id "
                    "ORDER BY version_number"
                ),
                {"source_id": source_id},
            ).mappings()
            return SourceDetailResponse(
                source=source,
                versions=[self._version_from_row(connection, row) for row in rows],
            )

    def list_sources(self, limit: int = 100) -> list[SourceRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM research_sources ORDER BY created_at_utc, id LIMIT :limit"),
                {"limit": limit},
            ).mappings()
            return [self._source_from_row(row) for row in rows]

    def get_source_version(self, source_version_id: UUID) -> SourceVersion:
        with self.engine.connect() as connection:
            return self._load_version(connection, source_version_id)

    def get_corroborating_versions(self, source_version_id: UUID) -> list[SourceVersion]:
        with self.engine.connect() as connection:
            ids = self._corroboration_ids(connection, source_version_id)
            return [self._load_version(connection, item) for item in ids]

    @staticmethod
    def _insert_event(
        connection: Connection,
        request_id: UUID,
        event_type: ExtractionEventType,
        *,
        attempt_number: int = 1,
        error_code: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        statement = text(
            """
            INSERT INTO extraction_events (
                id, extraction_request_id, attempt_number, event_type, error_code, payload
            ) VALUES (
                :id, :request_id, :attempt_number, :event_type, :error_code, :payload
            )
            """
        ).bindparams(bindparam("payload", type_=postgresql.JSONB))
        connection.execute(
            statement,
            {
                "id": uuid4(),
                "request_id": request_id,
                "attempt_number": attempt_number,
                "event_type": event_type.value,
                "error_code": error_code,
                "payload": dict(payload or {}),
            },
        )

    def _latest_event(self, connection: Connection, request_id: UUID) -> ExtractionEventType:
        value = connection.execute(
            text(
                "SELECT event_type FROM extraction_events "
                "WHERE extraction_request_id = :request_id "
                "ORDER BY event_sequence DESC LIMIT 1"
            ),
            {"request_id": request_id},
        ).scalar_one()
        return ExtractionEventType(value)

    def _request_from_row(self, connection: Connection, row: RowMapping) -> ExtractionRequestRecord:
        return ExtractionRequestRecord(
            extraction_request_id=row["id"],
            source_version_id=row["source_version_id"],
            extractor_kind=row["extractor_kind"],
            extractor_id=row["extractor_id"],
            extractor_version=row["extractor_version"],
            extraction_model_id=row["extraction_model_id"],
            extraction_model_revision=row["extraction_model_revision"],
            extraction_prompt_version=row["extraction_prompt_version"],
            extraction_prompt_sha256=row["extraction_prompt_sha256"],
            extraction_schema_version=row["extraction_schema_version"],
            extraction_config_sha256=row["extraction_config_sha256"],
            request_fingerprint=row["request_fingerprint"],
            rq_job_id=row["rq_job_id"],
            latest_event=self._latest_event(connection, row["id"]),
            requested_at_utc=row["requested_at_utc"],
        )

    def _load_request(self, connection: Connection, request_id: UUID) -> ExtractionRequestRecord:
        row = (
            connection.execute(
                text("SELECT * FROM extraction_requests WHERE id = :id"), {"id": request_id}
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise NotFoundError(f"extraction request {request_id} was not found")
        return self._request_from_row(connection, row)

    def create_extraction_request(
        self, source_version_id: UUID, profile: ExtractionProfile
    ) -> ExtractionRequestRecord:
        source = self.get_source_version(source_version_id)
        if source.content_state is ContentState.URL_ONLY_UNRETRIEVED or source.raw_text is None:
            raise SourceTextUnavailableError(
                "source version has no supplied text; URL retrieval is outside Phase 2"
            )
        fingerprint = extraction_fingerprint(source, profile)
        try:
            with self.engine.begin() as connection:
                existing = (
                    connection.execute(
                        text(
                            "SELECT * FROM extraction_requests "
                            "WHERE request_fingerprint = :fingerprint"
                        ),
                        {"fingerprint": fingerprint},
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is not None:
                    return self._request_from_row(connection, existing)
                request_id = uuid4()
                row = (
                    connection.execute(
                        text(
                            """
                        INSERT INTO extraction_requests (
                            id, source_version_id, extractor_kind, extractor_id, extractor_version,
                            extraction_model_id, extraction_model_revision,
                            extraction_prompt_version, extraction_prompt_sha256,
                            extraction_schema_version, extraction_config_sha256,
                            request_fingerprint, rq_job_id
                        ) VALUES (
                            :id, :source_version_id, :extractor_kind, :extractor_id,
                            :extractor_version, :extraction_model_id, :extraction_model_revision,
                            :extraction_prompt_version, :extraction_prompt_sha256,
                            :extraction_schema_version, :extraction_config_sha256,
                            :request_fingerprint, :rq_job_id
                        ) RETURNING *
                        """
                        ),
                        {
                            "id": request_id,
                            "source_version_id": source_version_id,
                            "extractor_kind": profile.extractor_kind.value,
                            "extractor_id": profile.extractor_id,
                            "extractor_version": profile.extractor_version,
                            "extraction_model_id": profile.extraction_model_id,
                            "extraction_model_revision": profile.extraction_model_revision,
                            "extraction_prompt_version": profile.extraction_prompt_version,
                            "extraction_prompt_sha256": profile.extraction_prompt_sha256,
                            "extraction_schema_version": profile.extraction_schema_version,
                            "extraction_config_sha256": profile.extraction_config_sha256,
                            "request_fingerprint": fingerprint,
                            "rq_job_id": f"phase2-extract-{fingerprint}",
                        },
                    )
                    .mappings()
                    .one()
                )
                self._insert_event(connection, request_id, ExtractionEventType.REQUESTED)
                return self._request_from_row(connection, row)
        except IntegrityError:
            with self.engine.connect() as connection:
                existing = (
                    connection.execute(
                        text(
                            "SELECT * FROM extraction_requests "
                            "WHERE request_fingerprint = :fingerprint"
                        ),
                        {"fingerprint": fingerprint},
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is None:
                    raise
                return self._request_from_row(connection, existing)

    def record_event(
        self,
        request_id: UUID,
        event_type: ExtractionEventType,
        *,
        attempt_number: int = 1,
        error_code: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> ExtractionRequestRecord:
        with self.engine.begin() as connection:
            self._load_request(connection, request_id)
            self._insert_event(
                connection,
                request_id,
                event_type,
                attempt_number=attempt_number,
                error_code=error_code,
                payload=payload,
            )
            return self._load_request(connection, request_id)

    def get_extraction_request(self, request_id: UUID) -> ExtractionRequestRecord:
        with self.engine.connect() as connection:
            return self._load_request(connection, request_id)

    def list_extraction_requests(self, limit: int = 100) -> list[ExtractionRequestRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM extraction_requests ORDER BY requested_at_utc, id LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
            return [self._request_from_row(connection, row) for row in rows]

    @staticmethod
    def _card_from_payload(payload: Mapping[str, Any]) -> TradingIdeaCard:
        return TradingIdeaCard.model_validate(payload)

    @staticmethod
    def _memo_from_row(row: RowMapping) -> ResearchMemo:
        return ResearchMemo(
            memo_id=row["id"],
            card_id=row["card_id"],
            template_version=row["template_version"],
            markdown=row["markdown_content"],
            content_sha256=row["content_sha256"],
            created_at_utc=row["created_at_utc"],
        )

    def get_card_for_request(self, request_id: UUID) -> TradingIdeaCard | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT payload FROM trading_idea_cards "
                        "WHERE extraction_request_id = :request_id"
                    ),
                    {"request_id": request_id},
                )
                .mappings()
                .one_or_none()
            )
            return None if row is None else self._card_from_payload(row["payload"])

    def complete_extraction(
        self,
        request_id: UUID,
        card: TradingIdeaCard,
        memo: ResearchMemo,
        draft: ExtractionDraft,
    ) -> TradingIdeaCard:
        request = self.get_extraction_request(request_id)
        if card.extraction_request_id != request_id:
            raise ValueError("card lineage does not match the extraction request")
        if card.source_version_id != request.source_version_id:
            raise ValueError("card source lineage does not match the extraction request")
        if memo.card_id != card.card_id:
            raise ValueError("memo lineage does not match the card")
        card_profile = {
            "extractor_kind": card.extractor_kind,
            "extractor_id": card.extractor_id,
            "extractor_version": card.extractor_version,
            "extraction_model_id": card.extraction_model_id,
            "extraction_model_revision": card.extraction_model_revision,
            "extraction_prompt_version": card.extraction_prompt_version,
            "extraction_prompt_sha256": card.extraction_prompt_sha256,
            "extraction_schema_version": card.extraction_schema_version,
            "extraction_config_sha256": card.extraction_config_sha256,
        }
        request_profile = request.model_dump(include=set(card_profile))
        if card_profile != request_profile:
            raise ValueError("card extraction provenance does not match the immutable request")
        card_payload = card.model_dump(mode="json")
        draft_payload = draft.model_dump(mode="json")
        card_sha256 = _canonical_sha256(card_payload)
        try:
            with self.engine.begin() as connection:
                existing = (
                    connection.execute(
                        text(
                            "SELECT payload FROM trading_idea_cards "
                            "WHERE extraction_request_id = :request_id"
                        ),
                        {"request_id": request_id},
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is not None:
                    return self._card_from_payload(existing["payload"])
                statement = text(
                    """
                    INSERT INTO trading_idea_cards (
                        id, extraction_request_id, testability_status, testability_score,
                        infra_risk, corroboration_status, contribution_status,
                        research_priority_score, card_sha256, draft_payload, payload
                    ) VALUES (
                        :id, :request_id, :testability_status, :testability_score,
                        :infra_risk, :corroboration_status, :contribution_status,
                        :research_priority_score, :card_sha256, :draft_payload, :payload
                    )
                    """
                ).bindparams(
                    bindparam("draft_payload", type_=postgresql.JSONB),
                    bindparam("payload", type_=postgresql.JSONB),
                )
                connection.execute(
                    statement,
                    {
                        "id": card.card_id,
                        "request_id": request_id,
                        "testability_status": card.testability_status.value,
                        "testability_score": card.testability_score,
                        "infra_risk": card.infra_risk.value,
                        "corroboration_status": card.corroboration_status.value,
                        "contribution_status": card.contribution_status.value,
                        "research_priority_score": None,
                        "card_sha256": card_sha256,
                        "draft_payload": draft_payload,
                        "payload": card_payload,
                    },
                )
                for official_version_id in card.official_corroboration_source_version_ids:
                    connection.execute(
                        text(
                            "INSERT INTO card_official_corroborations "
                            "(card_id, official_source_version_id) "
                            "VALUES (:card_id, :official_source_version_id)"
                        ),
                        {
                            "card_id": card.card_id,
                            "official_source_version_id": official_version_id,
                        },
                    )
                connection.execute(
                    text(
                        """
                        INSERT INTO research_memos (
                            id, card_id, template_version, markdown_content,
                            content_sha256, created_at_utc
                        ) VALUES (
                            :id, :card_id, :template_version, :markdown_content,
                            :content_sha256, :created_at_utc
                        )
                        """
                    ),
                    {
                        "id": memo.memo_id,
                        "card_id": memo.card_id,
                        "template_version": memo.template_version,
                        "markdown_content": memo.markdown,
                        "content_sha256": memo.content_sha256,
                        "created_at_utc": memo.created_at_utc,
                    },
                )
                self._insert_event(connection, request_id, ExtractionEventType.SUCCEEDED)
                return card
        except IntegrityError:
            existing_card = self.get_card_for_request(request_id)
            if existing_card is None:
                raise
            self.record_event(
                request_id,
                ExtractionEventType.SUCCEEDED,
                payload={"deduplicated_concurrent_worker": True},
            )
            return existing_card

    def get_card(self, card_id: UUID) -> CardWithMemo:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT payload FROM trading_idea_cards WHERE id = :id"), {"id": card_id}
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise NotFoundError(f"card {card_id} was not found")
            memo_row = (
                connection.execute(
                    text("SELECT * FROM research_memos WHERE card_id = :card_id"),
                    {"card_id": card_id},
                )
                .mappings()
                .one()
            )
            return CardWithMemo(
                card=self._card_from_payload(row["payload"]),
                memo=self._memo_from_row(memo_row),
            )

    def list_cards(self, limit: int = 100) -> list[TradingIdeaCard]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT payload FROM trading_idea_cards "
                    "ORDER BY created_at_utc, id LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
            return [self._card_from_payload(row["payload"]) for row in rows]

    def get_memo(self, card_id: UUID) -> ResearchMemo:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM research_memos WHERE card_id = :card_id"),
                    {"card_id": card_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise NotFoundError(f"memo for card {card_id} was not found")
            return self._memo_from_row(row)

    def source_create_response(
        self,
        source: SourceRecord,
        version: SourceVersion,
        extraction: ExtractionRequestRecord | None,
    ) -> SourceCreateResponse:
        return SourceCreateResponse(
            source=source,
            source_version=version,
            extraction=extraction,
        )
