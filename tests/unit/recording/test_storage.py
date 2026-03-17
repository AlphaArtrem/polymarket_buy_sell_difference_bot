from pathlib import Path

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.recording.storage import JsonlEventStore


def test_jsonl_event_store_writes_and_reads_orderbook_events(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    event = OrderBookEvent(
        market_id="market-1",
        side="YES",
        asks=[BookLevel(price=0.43, size=100)],
        timestamp_ms=1_700_000_000_000,
    )

    store.append(event)
    loaded = list(store.iter_events())

    assert loaded == [event]
