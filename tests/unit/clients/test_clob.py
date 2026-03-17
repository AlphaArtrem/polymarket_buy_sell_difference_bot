import json
from pathlib import Path

import httpx

from polymarket_arb.clients.clob import ClobClient


def test_fetch_order_books_normalizes_bulk_response() -> None:
    yes_book = json.loads(
        Path("tests/fixtures/clob/book_yes.json").read_text(encoding="utf-8")
    )
    no_book = json.loads(
        Path("tests/fixtures/clob/book_no.json").read_text(encoding="utf-8")
    )
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, json=[yes_book, no_book])

    client = ClobClient(
        client=httpx.Client(
            base_url="https://clob.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    books = client.fetch_order_books(["yes-token-abc", "no-token-abc"])

    assert captured["method"] == "POST"
    assert captured["path"] == "/books"
    assert '"token_id":"yes-token-abc"' in captured["body"]
    assert books["yes-token-abc"].asks[0].price == 0.43
    assert books["no-token-abc"].timestamp_ms == 1_700_000_000_001


def test_fetch_order_books_sorts_live_descending_asks_to_best_price_first() -> None:
    descending_book = {
        "market": "market-1",
        "asset_id": "yes-token-abc",
        "timestamp": "1700000000000",
        "bids": [
            {"price": "0.01", "size": "5"},
            {"price": "0.35", "size": "5"},
        ],
        "asks": [
            {"price": "0.99", "size": "5"},
            {"price": "0.36", "size": "5"},
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[descending_book])

    client = ClobClient(
        client=httpx.Client(
            base_url="https://clob.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    books = client.fetch_order_books(["yes-token-abc"])

    assert books["yes-token-abc"].asks[0].price == 0.36
    assert books["yes-token-abc"].bids[0].price == 0.35
