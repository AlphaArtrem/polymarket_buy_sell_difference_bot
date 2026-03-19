from pydantic import BaseModel

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.state.store import MarketStateStore


class MarketOpportunityStats(BaseModel):
    market_id: str
    slug: str
    question: str
    paired_snapshot_count: int = 0
    raw_opportunity_count: int = 0
    post_cost_opportunity_count: int = 0
    best_raw_sum: float | None = None
    best_net_sum: float | None = None


class OpportunityResearchReport(BaseModel):
    event_count: int
    paired_snapshot_count: int
    raw_opportunity_count: int
    post_cost_opportunity_count: int
    markets: list[MarketOpportunityStats]


def analyze_recorded_opportunities(
    *,
    catalog: list[MarketCatalogEntry],
    events: list[OrderBookEvent],
    stale_after_ms: int,
    fee_rate: float,
    slippage_buffer: float,
    operational_buffer: float,
) -> OpportunityResearchReport:
    state_store = MarketStateStore(stale_after_ms=stale_after_ms)
    market_stats = {
        entry.market_id: MarketOpportunityStats(
            market_id=entry.market_id,
            slug=entry.slug,
            question=entry.question,
        )
        for entry in catalog
    }
    paired_snapshot_count = 0
    raw_opportunity_count = 0
    post_cost_opportunity_count = 0

    for event in events:
        state_store.apply(event)
        try:
            paired = state_store.get_paired_book(event.market_id, event.timestamp_ms)
        except ValueError:
            continue
        if not paired.yes_asks or not paired.no_asks:
            continue

        raw_sum = _best_ask(paired.yes_asks) + _best_ask(paired.no_asks)
        net_sum = raw_sum + fee_rate + slippage_buffer + operational_buffer

        paired_snapshot_count += 1
        stats = market_stats[event.market_id]
        stats.paired_snapshot_count += 1
        stats.best_raw_sum = _min_value(stats.best_raw_sum, raw_sum)
        stats.best_net_sum = _min_value(stats.best_net_sum, net_sum)

        if raw_sum < 1.0:
            raw_opportunity_count += 1
            stats.raw_opportunity_count += 1
        if net_sum < 1.0:
            post_cost_opportunity_count += 1
            stats.post_cost_opportunity_count += 1

    return OpportunityResearchReport(
        event_count=len(events),
        paired_snapshot_count=paired_snapshot_count,
        raw_opportunity_count=raw_opportunity_count,
        post_cost_opportunity_count=post_cost_opportunity_count,
        markets=list(market_stats.values()),
    )


def _min_value(current: float | None, candidate: float) -> float:
    if current is None:
        return candidate
    return min(current, candidate)


def _best_ask(levels: list) -> float:
    return min(level.price for level in levels)
