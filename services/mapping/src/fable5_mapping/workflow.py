from __future__ import annotations

from uuid import UUID

from fable5_mapping.models import MappingWithRationale
from fable5_mapping.repository import MappingRepository


class MappingWorkflow:
    def __init__(self, repository: MappingRepository) -> None:
        self.repository = repository

    def create_mapping(self, card_id: UUID) -> MappingWithRationale:
        return self.repository.create_mapping(card_id)

    def get_mapping(self, mapping_id: UUID) -> MappingWithRationale:
        return self.repository.get_mapping(mapping_id)

    def list_mappings(
        self,
        *,
        card_id: UUID | None,
        limit: int,
    ) -> list[MappingWithRationale]:
        return self.repository.list_mappings(card_id=card_id, limit=limit)


__all__ = ["MappingWorkflow"]
