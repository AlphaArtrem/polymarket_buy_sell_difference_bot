from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
from polymarket_arb.research.opportunities import analyze_recorded_opportunities


def test_analyzer_counts_raw_and_post_cost_opportunities() -> None:
    catalog = [
        MarketCatalogEntry(
            market_id="m1",
            slug="market-one",
            question="Market one?",
            yes_token_id="yes-1",
            no_token_id="no-1",
            fees_enabled=False,
            max_capital_usd=50.0,
            active=True,
        )
    ]
    events = [
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[
                BookLevel(price=0.99, size=10.0),
                BookLevel(price=0.48, size=100.0),
            ],
            timestamp_ms=1_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[
                BookLevel(price=0.99, size=10.0),
                BookLevel(price=0.49, size=100.0),
            ],
            timestamp_ms=1_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[
                BookLevel(price=0.99, size=10.0),
                BookLevel(price=0.52, size=100.0),
            ],
            timestamp_ms=2_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[
                BookLevel(price=0.99, size=10.0),
                BookLevel(price=0.50, size=100.0),
            ],
            timestamp_ms=2_000,
        ),
    ]

    report = analyze_recorded_opportunities(
        catalog=catalog,
        events=events,
        stale_after_ms=5_000,
        fee_rate=0.005,
        slippage_buffer=0.002,
        operational_buffer=0.001,
    )

    assert report.event_count == 4
    assert report.paired_snapshot_count == 3
    assert report.raw_opportunity_count == 1
    assert report.post_cost_opportunity_count == 1
    assert len(report.markets) == 1
    assert report.markets[0].slug == "market-one"
    assert report.markets[0].paired_snapshot_count == 3
    assert report.markets[0].raw_opportunity_count == 1
    assert report.markets[0].post_cost_opportunity_count == 1
    assert report.markets[0].best_raw_sum == 0.97
    assert report.markets[0].best_net_sum == 0.978
