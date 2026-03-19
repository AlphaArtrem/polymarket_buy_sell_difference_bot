from polymarket_arb.config import ResearchSettings
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.research.market_quality import (
    MarketQualityReport,
    MarketQualityTracker,
)


def analyze_recorded_opportunities(
    *,
    catalog: list[MarketCatalogEntry],
    events: list[OrderBookEvent],
    stale_after_ms: int,
    fee_rate: float,
    slippage_buffer: float,
    operational_buffer: float,
    research: ResearchSettings | None = None,
) -> MarketQualityReport:
    tracker = MarketQualityTracker(
        catalog=catalog,
        stale_after_ms=stale_after_ms,
        fee_rate=fee_rate,
        slippage_buffer=slippage_buffer,
        operational_buffer=operational_buffer,
        research=research or ResearchSettings(),
    )
    for event in events:
        tracker.observe(event)
    return tracker.finalize(run_duration_seconds=_duration_seconds(events))


def _duration_seconds(events: list[OrderBookEvent]) -> float:
    if len(events) < 2:
        return 0.0
    return max((events[-1].timestamp_ms - events[0].timestamp_ms) / 1000, 0.0)
