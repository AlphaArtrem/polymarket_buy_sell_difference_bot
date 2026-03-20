from polymarket_arb.structure.models import StructureDefinition


def test_structure_definition_accepts_mutually_exclusive_group() -> None:
    definition = StructureDefinition(
        key="election-basket",
        relationship_type="mutually_exclusive_yes",
        market_slugs=["a", "b", "c"],
    )

    assert definition.relationship_type == "mutually_exclusive_yes"
    assert definition.market_slugs == ["a", "b", "c"]
