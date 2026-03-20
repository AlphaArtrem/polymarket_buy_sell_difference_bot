from polymarket_arb.structure.scanner import StructureScanner


def test_scan_structure_finds_mutually_exclusive_yes_basket_gap() -> None:
    scanner = StructureScanner(
        min_raw_gap_bps=25,
        min_net_gap_bps=10,
        fee_rate=0.0,
        slippage_buffer=0.0,
        operational_buffer=0.0,
    )

    opportunity = scanner.scan_mutually_exclusive_yes(
        key="election-basket",
        yes_quotes=[
            {"slug": "a", "price": 0.30, "size": 10},
            {"slug": "b", "price": 0.32, "size": 12},
            {"slug": "c", "price": 0.31, "size": 8},
        ],
    )

    assert opportunity is not None
    assert opportunity.raw_gap_bps == 700
    assert opportunity.executable_size == 8


def test_scan_structure_finds_implication_gap() -> None:
    scanner = StructureScanner(
        min_raw_gap_bps=25,
        min_net_gap_bps=10,
        fee_rate=0.0,
        slippage_buffer=0.0,
        operational_buffer=0.0,
    )

    opportunity = scanner.scan_implication_pair(
        key="a-implies-b",
        yes_child_price=0.62,
        no_parent_price=0.20,
        child_size=9,
        parent_size=7,
    )

    assert opportunity is not None
    assert opportunity.executable_size == 7
