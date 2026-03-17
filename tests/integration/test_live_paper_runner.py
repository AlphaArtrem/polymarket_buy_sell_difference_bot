from polymarket_arb.adapters.live import normalize_orderbook_payload
from polymarket_arb.engine import TradingEngine


def test_normalize_orderbook_payload_maps_yes_and_no_books() -> None:
    payload = {
        "market": "market-1",
        "side": "YES",
        "asks": [["0.43", "10"]],
        "timestamp": 1_700_000_000_000,
    }

    event = normalize_orderbook_payload(payload)

    assert event.market_id == "market-1"
    assert event.asks[0].price == 0.43


def test_live_adapter_events_drive_same_engine_decisions_as_replay() -> None:
    payloads = [
        {"market": "market-1", "side": "YES", "asks": [["0.43", "10"]], "timestamp": 1000},
        {"market": "market-1", "side": "NO", "asks": [["0.54", "10"]], "timestamp": 1001},
    ]

    engine = TradingEngine.from_defaults(starting_cash_usd=500)
    decisions = [engine.on_event(normalize_orderbook_payload(payload)) for payload in payloads]

    assert any(decision and decision.decision == "trade" for decision in decisions)
