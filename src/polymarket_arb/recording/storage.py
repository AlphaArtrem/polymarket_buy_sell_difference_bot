import json
from pathlib import Path
from typing import Iterable, List

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry


class ReplayInputError(FileNotFoundError):
    pass


class JsonlEventStore:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._run_dir / "events.jsonl"
        self._catalog_path = self._run_dir / "catalog.json"

    def append(self, event: OrderBookEvent) -> None:
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def iter_events(self, *, required: bool = False) -> Iterable[OrderBookEvent]:
        if not self._events_path.exists():
            if required:
                raise ReplayInputError("Missing replay input: events.jsonl")
            return []
        lines = self._events_path.read_text(encoding="utf-8").splitlines()
        if required and not lines:
            raise ReplayInputError("Replay input is empty: events.jsonl")
        return [
            OrderBookEvent.model_validate_json(line)
            for line in lines
        ]

    def write_catalog(self, catalog: List[MarketCatalogEntry]) -> None:
        self._catalog_path.write_text(
            json.dumps([entry.model_dump() for entry in catalog], indent=2) + "\n",
            encoding="utf-8",
        )

    def read_catalog(self, *, required: bool = False) -> List[MarketCatalogEntry]:
        if not self._catalog_path.exists():
            if required:
                raise ReplayInputError("Missing replay input: catalog.json")
            return []
        data = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        if required and not data:
            raise ReplayInputError("Replay input is empty: catalog.json")
        return [MarketCatalogEntry.model_validate(entry) for entry in data]

    def validate_replay_inputs(self) -> None:
        self.read_catalog(required=True)
        list(self.iter_events(required=True))
