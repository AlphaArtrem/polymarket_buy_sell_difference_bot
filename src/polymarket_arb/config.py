from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field


class ApiSettings(BaseModel):
    gamma_base_url: str
    clob_base_url: str
    market_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
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


class RuntimeSettings(BaseModel):
    mode: str = "poll"
    artifact_dir: str = "artifacts/runtime"
    polygon_rpc_url: str | None = None


class ResearchSettings(BaseModel):
    keep_min_paired_snapshots_per_minute: float = Field(ge=0, default=0)
    keep_min_post_cost_opportunities_per_minute: float = Field(ge=0, default=0)
    keep_min_total_time_in_edge_ms: int = Field(ge=0, default=0)
    keep_min_best_net_edge_bps: float = Field(ge=0, default=0)
    keep_min_max_window_ms: int = Field(ge=0, default=0)
    watch_min_paired_snapshots_per_minute: float = Field(ge=0, default=0)
    watch_min_post_cost_opportunities_per_minute: float = Field(ge=0, default=0)
    watch_min_best_net_edge_bps: float = Field(ge=0, default=0)
    low_sample_paired_snapshot_floor: int = Field(ge=0, default=0)


class Settings(BaseModel):
    venue: str
    api: ApiSettings
    markets: List[MarketSelection]
    strategy: StrategySettings
    portfolio: PortfolioSettings
    runtime: RuntimeSettings = RuntimeSettings()
    research: ResearchSettings = ResearchSettings()


def load_settings(path: Path) -> Settings:
    return Settings.model_validate(yaml.safe_load(path.read_text()))
