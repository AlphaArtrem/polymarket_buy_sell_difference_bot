from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.state.store import MarketStateStore


def test_market_state_store_tracks_yes_and_no_books() -> None:
    store = MarketStateStore(stale_after_ms=5_000)
    store.apply(
        OrderBookEvent(
            market_id="market-1",
            side="YES",
            asks=[BookLevel(price=0.43, size=50)],
            timestamp_ms=1_000,
        )
    )
    store.apply(
        OrderBookEvent(
            market_id="market-1",
            side="NO",
            asks=[BookLevel(price=0.54, size=50)],
            timestamp_ms=1_100,
        )
    )

    paired = store.get_paired_book("market-1", now_ms=1_200)

    assert paired.yes_asks[0].price == 0.43
    assert paired.no_asks[0].price == 0.54
    assert paired.is_fresh is True
