from pydantic import BaseModel

from polymarket_arb.domain.models import BookLevel


class OrderBookEvent(BaseModel):
    market_id: str
    side: str
    asks: list[BookLevel]
    timestamp_ms: int
