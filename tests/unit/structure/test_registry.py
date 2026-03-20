from pathlib import Path
from textwrap import dedent

from polymarket_arb.domain.models import EnrichedMarketEntry
from polymarket_arb.structure.models import StructureDefinition
from polymarket_arb.structure.registry import (
    StructureRegistry,
    load_structure_registry,
    resolve_structure_registry,
)


def test_load_structure_registry_reads_relationships(tmp_path: Path) -> None:
    registry_path = tmp_path / "structure_registry.yaml"
    registry_path.write_text(
        dedent(
            """
            relationships:
              - key: election-basket
                relationship_type: mutually_exclusive_yes
                market_slugs:
                  - will-a-win
                  - will-b-win
            """
        ).strip()
    )

    registry = load_structure_registry(registry_path)

    assert registry.relationships[0].key == "election-basket"


def test_resolve_structure_registry_maps_slugs_to_market_ids() -> None:
    registry = StructureRegistry(
        relationships=[
            StructureDefinition(
                key="basket",
                relationship_type="mutually_exclusive_yes",
                market_slugs=["will-a-win", "will-b-win"],
            )
        ]
    )
    catalog = [
        EnrichedMarketEntry(
            market_id="1",
            slug="will-a-win",
            question="Will A win?",
            yes_token_id="yes-a",
            no_token_id="no-a",
            fees_enabled=False,
            max_capital_usd=0.0,
        ),
        EnrichedMarketEntry(
            market_id="2",
            slug="will-b-win",
            question="Will B win?",
            yes_token_id="yes-b",
            no_token_id="no-b",
            fees_enabled=False,
            max_capital_usd=0.0,
        ),
    ]

    resolved = resolve_structure_registry(registry, catalog)

    assert resolved[0].market_ids == ["1", "2"]
