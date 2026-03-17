import time
from typing import Any, Callable, Iterable

from polymarket_arb.clients.clob import ClobClient, OrderBookSnapshot
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
        poll_interval_ms: int,
        monotonic_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._catalog = catalog
        self._clob_client = clob_client
        self._poll_interval_ms = poll_interval_ms
        self._monotonic_fn = monotonic_fn or time.monotonic
        self._sleep_fn = sleep_fn or time.sleep

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        catalog: list[MarketCatalogEntry],
        clob_client: ClobClient,
    ) -> "LiveAdapter":
        return cls(
            catalog=catalog,
            clob_client=clob_client,
            poll_interval_ms=settings.api.poll_interval_ms,
        )

    def iter_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        deadline = self._monotonic_fn() + max(limit_seconds, 0)
        first_poll = True
        while first_poll or self._monotonic_fn() < deadline:
            first_poll = False
            for event in self.poll_once():
                yield event
            if self._monotonic_fn() >= deadline:
                break
            self._sleep_fn(self._poll_interval_ms / 1000)

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


def snapshot_to_event(
    *, snapshot: OrderBookSnapshot, market_id: str, side: str
) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=market_id,
        side=side,
        asks=snapshot.asks,
        timestamp_ms=snapshot.timestamp_ms,
    )
