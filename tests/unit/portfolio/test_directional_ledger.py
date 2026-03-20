from polymarket_arb.portfolio.directional import DirectionalLedger


def test_directional_ledger_realizes_pnl_on_exit() -> None:
    ledger = DirectionalLedger(starting_cash_usd=500)
    trade_id = ledger.open_position(
        market_id="123",
        direction="YES",
        size=10,
        entry_price=0.42,
    )

    ledger.close_position(trade_id=trade_id, exit_price=0.58)

    assert ledger.realized_pnl_usd == 1.6
    assert ledger.free_cash_usd == 501.6
