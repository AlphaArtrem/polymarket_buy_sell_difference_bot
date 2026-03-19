from polymarket_arb.config import ResearchSettings
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
        research=ResearchSettings(
            keep_min_paired_snapshots_per_minute=1,
            keep_min_post_cost_opportunities_per_minute=1,
            keep_min_total_time_in_edge_ms=0,
            keep_min_best_net_edge_bps=100,
            keep_min_max_window_ms=0,
            watch_min_paired_snapshots_per_minute=0,
            watch_min_post_cost_opportunities_per_minute=0,
            watch_min_best_net_edge_bps=0,
            low_sample_paired_snapshot_floor=1,
        ),
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
    assert report.markets[0].best_net_edge_bps == 220
    assert report.markets[0].status == "keep"
    assert "passes_keep_thresholds" in report.markets[0].reasons


def test_analyzer_classifies_quiet_market_as_drop() -> None:
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
            asks=[BookLevel(price=0.60, size=100.0)],
            timestamp_ms=1_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.39, size=100.0)],
            timestamp_ms=1_000,
        ),
    ]

    report = analyze_recorded_opportunities(
        catalog=catalog,
        events=events,
        stale_after_ms=5_000,
        fee_rate=0.005,
        slippage_buffer=0.002,
        operational_buffer=0.001,
        research=ResearchSettings(
            keep_min_paired_snapshots_per_minute=10,
            keep_min_post_cost_opportunities_per_minute=1,
            keep_min_total_time_in_edge_ms=3_000,
            keep_min_best_net_edge_bps=100,
            keep_min_max_window_ms=1_500,
            watch_min_paired_snapshots_per_minute=5,
            watch_min_post_cost_opportunities_per_minute=0.5,
            watch_min_best_net_edge_bps=20,
            low_sample_paired_snapshot_floor=3,
        ),
    )

    assert report.markets[0].status == "drop"
    assert "too_quiet" in report.markets[0].reasons
