import json
from pathlib import Path

from polymarket_arb.adapters.live import LiveAdapter
from polymarket_arb.clients.clob import OrderBookSnapshot
from polymarket_arb.domain.models import MarketCatalogEntry


def test_live_adapter_bootstraps_books_then_emits_stream_updates() -> None:
    yes_book = json.loads(
        Path("tests/fixtures/clob/book_yes.json").read_text(encoding="utf-8")
    )
    no_book = json.loads(
        Path("tests/fixtures/clob/book_no.json").read_text(encoding="utf-8")
    )
    ws_message = json.loads(
        Path("tests/fixtures/clob/ws_market_book.json").read_text(encoding="utf-8")
    )

    catalog = [
        MarketCatalogEntry(
            market_id="0xabc",
            slug="market",
            question="Question?",
            yes_token_id="yes-token-1",
            no_token_id="no-token-abc",
            fees_enabled=True,
            max_capital_usd=50,
        )
    ]

    class StubClobClient:
        def fetch_order_books(self, token_ids: list[str]) -> dict[str, OrderBookSnapshot]:
            assert token_ids == ["yes-token-1", "no-token-abc"]
            yes_payload = dict(yes_book)
            yes_payload["asset_id"] = "yes-token-1"
            yes_payload["market"] = "0xabc"
            return {
                "yes-token-1": OrderBookSnapshot.model_validate(yes_payload),
                "no-token-abc": OrderBookSnapshot.model_validate(no_book),
            }

    class StubWsClient:
        async def subscribe_market(self, url: str, asset_ids: list[str]):
            assert url.endswith("/ws/market")
            assert asset_ids == ["yes-token-1", "no-token-abc"]
            yield json.dumps([ws_message])

    adapter = LiveAdapter(
        catalog=catalog,
        clob_client=StubClobClient(),
        clob_ws_client=StubWsClient(),
        poll_interval_ms=1,
        runtime_mode="stream",
        market_ws_url="wss://ws-subscriptions-clob.polymarket.com/ws/market",
    )

    events = list(adapter.iter_events(limit_seconds=1))

    assert events[0].side == "YES"
    assert events[1].side == "NO"
    assert events[-1].side == "YES"
    assert events[-1].asks[0].price == 0.41
