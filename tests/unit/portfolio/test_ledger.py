from polymarket_arb.portfolio.ledger import PortfolioLedger


def test_portfolio_ledger_realizes_profit_on_resolution() -> None:
    ledger = PortfolioLedger(starting_cash_usd=500, free_cash_usd=500)
    ledger.open_pair(total_cost=97)
    ledger.resolve_pair(total_cost=97, payout=100)
    assert ledger.free_cash_usd == 503
    assert ledger.realized_pnl_usd == 3
