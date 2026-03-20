from polymarket_arb.research.event_paper import EventPaperRunner


def test_event_paper_runner_creates_trade_for_accepted_signal() -> None:
    runner = EventPaperRunner(
        starting_cash_usd=500,
        max_total_deployed_usd=200,
        default_exit_mode="repricing_target",
    )

    result = runner.on_signal(
        market_id="123",
        slug="will-example-happen",
        direction="YES",
        expected_edge_bps=40,
        best_ask=0.42,
        available_size=10,
        timestamp_ms=1_700_000_000_000,
    )

    assert result.decision == "trade"
    assert result.trade.direction == "YES"
