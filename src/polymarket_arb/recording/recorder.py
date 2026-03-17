from typing import List

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.recording.storage import JsonlEventStore


class Recorder:
    def __init__(self, store: JsonlEventStore) -> None:
        self._store = store

    def start_run(self, catalog: List[MarketCatalogEntry]) -> None:
        self._store.write_catalog(catalog)

    def record(self, event: OrderBookEvent) -> None:
        self._store.append(event)
