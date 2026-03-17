from typing import Iterable

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.recording.storage import JsonlEventStore


class ReplayAdapter:
    def __init__(self, store: JsonlEventStore) -> None:
        self._store = store

    def iter_events(self) -> Iterable[OrderBookEvent]:
        return self._store.iter_events()
