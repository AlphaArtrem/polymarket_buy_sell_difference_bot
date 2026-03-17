from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field


class ApiSettings(BaseModel):
    gamma_base_url: str
    clob_base_url: str
    poll_interval_ms: int = Field(gt=0)
    catalog_output_path: str | None = None


class MarketSelection(BaseModel):
    slug: str
    max_capital_usd: float = Field(gt=0)


class StrategySettings(BaseModel):
    raw_alert_threshold: float = Field(gt=0, lt=1)
    fee_rate: float = Field(ge=0, lt=1)
    slippage_buffer: float = Field(ge=0, lt=1)
    operational_buffer: float = Field(ge=0, lt=1)
    stale_after_ms: int = Field(gt=0)


class PortfolioSettings(BaseModel):
    starting_cash_usd: float = Field(gt=0)
    max_total_deployed_usd: float = Field(gt=0)


class Settings(BaseModel):
    venue: str
    api: ApiSettings
    markets: List[MarketSelection]
    strategy: StrategySettings
    portfolio: PortfolioSettings


def load_settings(path: Path) -> Settings:
    return Settings.model_validate(yaml.safe_load(path.read_text()))
