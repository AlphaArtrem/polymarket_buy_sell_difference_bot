from dataclasses import dataclass, field

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel


@dataclass
class PairedBook:
    yes_asks: list[BookLevel] = field(default_factory=list)
    no_asks: list[BookLevel] = field(default_factory=list)
    last_yes_ms: int = 0
    last_no_ms: int = 0

    @property
    def is_fresh(self) -> bool:
        return self.last_yes_ms > 0 and self.last_no_ms > 0


class MarketStateStore:
    def __init__(self, stale_after_ms: int) -> None:
        self._stale_after_ms = stale_after_ms
        self._books: dict[str, PairedBook] = {}

    def apply(self, event: OrderBookEvent) -> None:
        book = self._books.setdefault(event.market_id, PairedBook())
        if event.side == "YES":
            book.yes_asks = event.asks
            book.last_yes_ms = event.timestamp_ms
        else:
            book.no_asks = event.asks
            book.last_no_ms = event.timestamp_ms

    def get_paired_book(self, market_id: str, now_ms: int) -> PairedBook:
        book = self._books[market_id]
        if now_ms - max(book.last_yes_ms, book.last_no_ms) > self._stale_after_ms:
            raise ValueError("stale market data")
        return book
