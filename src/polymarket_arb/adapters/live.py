import asyncio
import json
import time
from typing import Any, Callable, Iterable

from polymarket_arb.clients.clob import (
    ClobClient,
    ClobMarketStreamMessage,
    ClobWebSocketClient,
    OrderBookSnapshot,
    normalize_market_ws_message,
)
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry


def normalize_orderbook_payload(payload: dict[str, Any]) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=str(payload["market"]),
        side=str(payload["side"]),
        asks=[
            BookLevel(price=float(price), size=float(size))
            for price, size in payload["asks"]
        ],
        timestamp_ms=int(payload["timestamp"]),
    )


class LiveAdapter:
    def __init__(
        self,
        *,
        catalog: list[MarketCatalogEntry],
        clob_client: ClobClient,
        clob_ws_client: ClobWebSocketClient | None = None,
        poll_interval_ms: int,
        runtime_mode: str = "poll",
        market_ws_url: str | None = None,
        monotonic_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._catalog = catalog
        self._clob_client = clob_client
        self._clob_ws_client = clob_ws_client
        self._poll_interval_ms = poll_interval_ms
        self._runtime_mode = runtime_mode
        self._market_ws_url = market_ws_url
        self._monotonic_fn = monotonic_fn or time.monotonic
        self._sleep_fn = sleep_fn or time.sleep
        self._asset_index = {
            entry.yes_token_id: (entry.market_id, "YES")
            for entry in self._catalog
        } | {
            entry.no_token_id: (entry.market_id, "NO")
            for entry in self._catalog
        }
        self._feed_health = {
            "mode": runtime_mode,
            "events_seen": 0,
            "stream_messages_seen": 0,
            "stale_feed_events": 0,
            "reconnects": 0,
        }

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        catalog: list[MarketCatalogEntry],
        clob_client: ClobClient,
        clob_ws_client: ClobWebSocketClient | None = None,
        runtime_mode: str | None = None,
    ) -> "LiveAdapter":
        return cls(
            catalog=catalog,
            clob_client=clob_client,
            clob_ws_client=clob_ws_client,
            poll_interval_ms=settings.api.poll_interval_ms,
            runtime_mode=runtime_mode or settings.runtime.mode,
            market_ws_url=settings.api.market_ws_url,
        )

    def iter_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        if self._runtime_mode == "stream":
            yield from self.iter_streaming_events(limit_seconds=limit_seconds)
            return
        yield from self.iter_polling_events(limit_seconds=limit_seconds)

    def iter_polling_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        deadline = self._monotonic_fn() + max(limit_seconds, 0)
        first_poll = True
        while first_poll or self._monotonic_fn() < deadline:
            first_poll = False
            for event in self.poll_once():
                self._track_event()
                yield event
            if self._monotonic_fn() >= deadline:
                break
            self._sleep_fn(self._poll_interval_ms / 1000)

    def iter_streaming_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        for event in self.poll_once():
            self._track_event()
            yield event

        if self._clob_ws_client is None or self._market_ws_url is None:
            return

        deadline = self._monotonic_fn() + max(limit_seconds, 0)
        for event in self._collect_stream_events(deadline):
            self._track_event()
            yield event

    def poll_once(self) -> list[OrderBookEvent]:
        token_ids = [
            token_id
            for entry in self._catalog
            for token_id in (entry.yes_token_id, entry.no_token_id)
        ]
        snapshots = self._clob_client.fetch_order_books(token_ids)
        events: list[OrderBookEvent] = []
        for entry in self._catalog:
            yes_snapshot = snapshots.get(entry.yes_token_id)
            no_snapshot = snapshots.get(entry.no_token_id)
            if yes_snapshot is not None:
                events.append(
                    snapshot_to_event(
                        snapshot=yes_snapshot,
                        market_id=entry.market_id,
                        side="YES",
                    )
                )
            if no_snapshot is not None:
                events.append(
                    snapshot_to_event(
                        snapshot=no_snapshot,
                        market_id=entry.market_id,
                        side="NO",
                    )
                )
        return events

    def feed_health(self) -> dict[str, int | str]:
        return dict(self._feed_health)

    def _track_event(self) -> None:
        self._feed_health["events_seen"] += 1

    def _collect_stream_events(self, deadline: float) -> list[OrderBookEvent]:
        return asyncio.run(self._collect_stream_events_async(deadline))

    async def _collect_stream_events_async(self, deadline: float) -> list[OrderBookEvent]:
        asset_ids = list(self._asset_index)
        iterator = self._clob_ws_client.subscribe_market(
            self._market_ws_url,
            asset_ids,
        ).__aiter__()
        events: list[OrderBookEvent] = []
        while self._monotonic_fn() < deadline:
            remaining = max(deadline - self._monotonic_fn(), 0.001)
            try:
                raw_message = await asyncio.wait_for(
                    iterator.__anext__(),
                    timeout=remaining,
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                self._feed_health["stale_feed_events"] += 1
                break

            self._feed_health["stream_messages_seen"] += 1
            event = self._normalize_stream_message(raw_message)
            if event is not None:
                events.append(event)
        return events

    def _normalize_stream_message(self, raw_message: str | dict[str, Any]) -> OrderBookEvent | None:
        payload = (
            json.loads(raw_message)
            if isinstance(raw_message, str)
            else raw_message
        )
        message = normalize_market_ws_message(payload)
        if message.event_type != "book" or message.asset_id is None:
            return None
        if message.asset_id not in self._asset_index or message.timestamp_ms is None:
            return None
        market_id, side = self._asset_index[message.asset_id]
        return stream_message_to_event(
            message=message,
            market_id=market_id,
            side=side,
        )


def snapshot_to_event(
    *, snapshot: OrderBookSnapshot, market_id: str, side: str
) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=market_id,
        side=side,
        asks=snapshot.asks,
        timestamp_ms=snapshot.timestamp_ms,
    )


def stream_message_to_event(
    *, message: ClobMarketStreamMessage, market_id: str, side: str
) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=market_id,
        side=side,
        asks=message.asks,
        timestamp_ms=message.timestamp_ms or 0,
    )
