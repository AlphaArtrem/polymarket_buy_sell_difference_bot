from typing import Any, AsyncIterator

import httpx
import websockets

from polymarket_arb.domain.models import OrderBookSnapshot


class ClobWebSocketClient:
    async def subscribe(self, url: str) -> AsyncIterator[str]:
        async with websockets.connect(url) as websocket:
            async for message in websocket:
                yield message


class ClobClient:
    def __init__(
        self,
        base_url: str = "https://clob.polymarket.com",
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=10.0)

    def fetch_order_book(self, token_id: str) -> OrderBookSnapshot:
        response = self._client.get("/book", params={"token_id": token_id})
        response.raise_for_status()
        return OrderBookSnapshot.model_validate(response.json())

    def fetch_order_books(self, token_ids: list[str]) -> dict[str, OrderBookSnapshot]:
        if not token_ids:
            return {}
        response = self._client.post(
            "/books",
            json=[{"token_id": token_id} for token_id in token_ids],
        )
        response.raise_for_status()
        return normalize_order_books_payload(response.json())


def normalize_order_books_payload(payload: Any) -> dict[str, OrderBookSnapshot]:
    books = payload.get("data", payload) if isinstance(payload, dict) else payload
    snapshots = [OrderBookSnapshot.model_validate(book) for book in books]
    return {snapshot.asset_id: snapshot for snapshot in snapshots}


__all__ = ["ClobClient", "ClobWebSocketClient", "OrderBookSnapshot"]
