from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookLevel(BaseModel):
    price: float
    size: float


class MarketCatalogEntry(BaseModel):
    market_id: str
    slug: str
    question: str
    yes_token_id: str
    no_token_id: str
    fees_enabled: bool
    max_capital_usd: float
    active: bool = True


class OrderBookSnapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    market: str
    asset_id: str
    timestamp_ms: int = Field(alias="timestamp")
    asks: list[BookLevel]
    bids: list[BookLevel] = Field(default_factory=list)
    tick_size: float | None = None
    neg_risk: bool | None = None

    @field_validator("timestamp_ms", mode="before")
    @classmethod
    def parse_timestamp_ms(cls, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            if value.isdigit():
                return int(value)
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(parsed.timestamp() * 1000)
        raise TypeError("Unsupported timestamp format")

    @field_validator("asks", "bids", mode="before")
    @classmethod
    def parse_levels(cls, value: object) -> list[BookLevel]:
        if value is None:
            return []
        levels: list[BookLevel] = []
        for raw_level in value:
            if isinstance(raw_level, dict):
                levels.append(
                    BookLevel(
                        price=float(raw_level["price"]),
                        size=float(raw_level["size"]),
                    )
                )
                continue
            price, size = raw_level
            levels.append(BookLevel(price=float(price), size=float(size)))
        return levels


class Opportunity(BaseModel):
    market_id: str
    yes_ask: float
    no_ask: float
    estimated_net_cost: float
    paired_size: float
