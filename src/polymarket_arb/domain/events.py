from pydantic import BaseModel, field_validator

from polymarket_arb.domain.models import BookLevel


class OrderBookEvent(BaseModel):
    market_id: str
    side: str
    asks: list[BookLevel]
    timestamp_ms: int

    @field_validator("asks")
    @classmethod
    def sort_asks(cls, value: list[BookLevel]) -> list[BookLevel]:
        return sorted(value, key=lambda level: level.price)
