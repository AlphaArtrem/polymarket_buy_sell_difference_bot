from pathlib import Path

import yaml
from pydantic import BaseModel

from polymarket_arb.domain.models import EnrichedMarketEntry
from polymarket_arb.structure.models import ResolvedStructureDefinition, StructureDefinition


class StructureRegistry(BaseModel):
    relationships: list[StructureDefinition]


def load_structure_registry(path: Path) -> StructureRegistry:
    return StructureRegistry.model_validate(yaml.safe_load(path.read_text()))


def resolve_structure_registry(
    registry: StructureRegistry,
    catalog: list[EnrichedMarketEntry],
) -> list[ResolvedStructureDefinition]:
    market_ids_by_slug = {entry.slug: entry.market_id for entry in catalog}
    resolved: list[ResolvedStructureDefinition] = []
    for relationship in registry.relationships:
        market_ids = [
            market_ids_by_slug[slug]
            for slug in relationship.market_slugs
            if slug in market_ids_by_slug
        ]
        if len(market_ids) != len(relationship.market_slugs):
            continue
        resolved.append(
            ResolvedStructureDefinition(
                key=relationship.key,
                relationship_type=relationship.relationship_type,
                market_slugs=relationship.market_slugs,
                market_ids=market_ids,
            )
        )
    return resolved
