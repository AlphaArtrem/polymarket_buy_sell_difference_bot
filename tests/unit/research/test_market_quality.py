from polymarket_arb.config import ResearchSettings
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
from polymarket_arb.research.market_quality import (
    MarketQualityTracker,
    summarize_window_durations,
)


def _catalog() -> list[MarketCatalogEntry]:
    return [
        MarketCatalogEntry(
            market_id="m1",
            slug="market-one",
            question="Market one?",
            yes_token_id="yes-1",
            no_token_id="no-1",
            fees_enabled=False,
            max_capital_usd=50,
            active=True,
        )
    ]


def _research() -> ResearchSettings:
    return ResearchSettings(
        keep_min_paired_snapshots_per_minute=8,
        keep_min_post_cost_opportunities_per_minute=1,
        keep_min_total_time_in_edge_ms=3000,
        keep_min_best_net_edge_bps=15,
        keep_min_max_window_ms=1500,
        watch_min_paired_snapshots_per_minute=3,
        watch_min_post_cost_opportunities_per_minute=0.2,
        watch_min_best_net_edge_bps=5,
        low_sample_paired_snapshot_floor=1,
    )


def test_market_quality_tracker_counts_windows_and_edge_time() -> None:
    tracker = MarketQualityTracker(
        catalog=_catalog(),
        stale_after_ms=5_000,
        fee_rate=0.005,
        slippage_buffer=0.002,
        operational_buffer=0.001,
        research=_research(),
    )

    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.48, size=100.0)],
            timestamp_ms=1_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.49, size=100.0)],
            timestamp_ms=1_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.48, size=100.0)],
            timestamp_ms=3_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.55, size=100.0)],
            timestamp_ms=7_000,
        )
    )

    report = tracker.finalize(run_duration_seconds=7)
    market = report.markets[0]

    assert market.post_cost_opportunity_count == 2
    assert market.opportunity_window_count == 1
    assert market.total_time_in_edge_ms == 6_000
    assert market.max_window_ms == 6_000


def test_summarize_window_durations_returns_percentiles() -> None:
    summary = summarize_window_durations([500, 1_500, 4_000])

    assert summary["p50_window_ms"] == 1_500
    assert summary["p95_window_ms"] == 4_000
    assert summary["max_window_ms"] == 4_000
