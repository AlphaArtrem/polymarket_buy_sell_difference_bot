from polymarket_arb.domain.models import BookLevel
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
        asks=[BookLevel(price=0.42, size=10)],
        bids=[BookLevel(price=0.48, size=10)],
        timestamp_ms=1_700_000_000_000,
    )

    assert result.decision == "trade"
    assert result.trade.direction == "YES"


def test_event_paper_runner_rejects_unfilled_entry() -> None:
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
        asks=[],
        bids=[],
        timestamp_ms=1_700_000_000_000,
    )

    assert result.decision == "reject"
    assert result.reason == "entry_no_fill"


def test_event_paper_runner_records_open_position_when_exit_not_triggered() -> None:
    runner = EventPaperRunner(
        starting_cash_usd=500,
        max_total_deployed_usd=200,
        default_exit_mode="repricing_target",
    )
    opened = runner.on_signal(
        market_id="123",
        slug="will-example-happen",
        direction="YES",
        expected_edge_bps=40,
        asks=[BookLevel(price=0.42, size=10)],
        bids=[BookLevel(price=0.42, size=10)],
        timestamp_ms=1_700_000_000_000,
    )

    outcome = runner.evaluate_open_position(
        trade_id=opened.trade.trade_id,
        market_id="123",
        bids=[BookLevel(price=0.42, size=10)],
        current_timestamp_ms=1_700_000_030_000,
        terminal_signal=False,
    )

    assert outcome.decision == "hold"
