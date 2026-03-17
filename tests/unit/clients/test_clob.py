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
