from pathlib import Path

from polymarket_arb.engine import TradingEngine
from polymarket_arb.adapters.replay import ReplayAdapter
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.recording.storage import JsonlEventStore


def test_replay_adapter_yields_events_in_recorded_order(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    first = OrderBookEvent(
        market_id="market-1",
        side="YES",
        asks=[BookLevel(price=0.43, size=10)],
        timestamp_ms=1000,
    )
    second = OrderBookEvent(
        market_id="market-1",
        side="NO",
        asks=[BookLevel(price=0.54, size=10)],
        timestamp_ms=1001,
    )
    store.append(first)
    store.append(second)

    replayed = list(ReplayAdapter(store).iter_events())

    assert replayed == [first, second]


def test_trading_engine_emits_trade_for_executable_pair(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    store.append(
        OrderBookEvent(
            market_id="market-1",
            side="YES",
            asks=[BookLevel(price=0.43, size=10)],
            timestamp_ms=1000,
        )
    )
    store.append(
        OrderBookEvent(
            market_id="market-1",
            side="NO",
            asks=[BookLevel(price=0.54, size=10)],
            timestamp_ms=1001,
        )
    )

    engine = TradingEngine.from_defaults(starting_cash_usd=500)
    results = [engine.on_event(event) for event in ReplayAdapter(store).iter_events()]

    assert any(result and result.decision == "trade" for result in results)
