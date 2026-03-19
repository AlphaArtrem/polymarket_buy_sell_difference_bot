import json
from pathlib import Path

from polymarket_arb.clients.clob import (
    build_market_subscription,
    normalize_market_ws_message,
)


def test_normalize_market_ws_message_extracts_book_update() -> None:
    payload = json.loads(
        Path("tests/fixtures/clob/ws_market_book.json").read_text(encoding="utf-8")
    )

    message = normalize_market_ws_message(payload)

    assert message.event_type == "book"
    assert message.asset_id == "yes-token-1"
    assert message.asks[0].price == 0.41


def test_build_market_subscription_uses_assets_ids() -> None:
    payload = build_market_subscription(["yes-token-1", "no-token-1"])

    assert payload["assets_ids"] == ["yes-token-1", "no-token-1"]
    assert payload["type"] == "market"
