# Polymarket Arbitrage V1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a beginner-safe Polymarket binary full-set arbitrage simulator that records market data, replays the same normalized events in backtests, and runs the same logic in live paper-trading mode.

**Architecture:** Use a Python `src/` layout with one shared event-driven core and two adapters: one for recorded replay data and one for live market streams. Keep market math, execution simulation, inventory tracking, and reporting isolated in small modules so replay and live paper modes only differ at the input boundary.

**Tech Stack:** Python 3.12, `typer`, `httpx`, `websockets`, `PyYAML`, `pydantic`, `pytest`, `pytest-asyncio`

---

## Scope Check

The spec is still one coherent subsystem, but the first implementation should stop at `Phase 1: Shared Replay And Live Paper Core`.

This plan intentionally excludes:

- real-money order placement
- maker orders
- broad automated market discovery
- merge execution
- Hyperliquid support

## File Structure

### Workspace Files

- Create: `pyproject.toml`
  Python package metadata, dependency list, pytest config, CLI entrypoint.
- Create: `.gitignore`
  Ignore local caches, `.superpowers/`, `.venv/`, and generated artifacts.
- Create: `README.md`
  Short project intro and local developer quickstart.
- Create: `configs/markets.sample.yaml`
  Starter config for curated market allowlist, thresholds, and risk caps.
- Create: `artifacts/.gitkeep`
  Keeps the output directory in place without checking in generated data.

### Package Layout

- Create: `src/polymarket_arb/__init__.py`
  Package marker and version export.
- Create: `src/polymarket_arb/cli.py`
  Typer app exposing `catalog-refresh`, `record-live`, `run-replay`, and `run-paper`.
- Create: `src/polymarket_arb/config.py`
  Config models and YAML loader.
- Create: `src/polymarket_arb/domain/models.py`
  Stable data models for catalog entries, book levels, opportunities, fills, lots, and portfolio snapshots.
- Create: `src/polymarket_arb/domain/events.py`
  Normalized market event types shared by recorder, replay, and live modes.
- Create: `src/polymarket_arb/clients/gamma.py`
  HTTP client for market metadata and token mapping.
- Create: `src/polymarket_arb/clients/clob.py`
  HTTP and WebSocket helpers for orderbook polling/streaming.
- Create: `src/polymarket_arb/catalog/service.py`
  Allowlist resolution and binary-market validation.
- Create: `src/polymarket_arb/recording/storage.py`
  JSONL and snapshot persistence for deterministic replay artifacts.
- Create: `src/polymarket_arb/recording/recorder.py`
  Service that writes normalized events from the live adapter into a run directory.
- Create: `src/polymarket_arb/adapters/replay.py`
  Reads recorded events back into the shared engine.
- Create: `src/polymarket_arb/adapters/live.py`
  Produces normalized events from current market data.
- Create: `src/polymarket_arb/state/store.py`
  Paired `YES` and `NO` orderbook state with freshness checks.
- Create: `src/polymarket_arb/strategy/opportunity.py`
  Net-cost calculation and opportunity rejection logic.
- Create: `src/polymarket_arb/strategy/sizing.py`
  Position sizing under depth and portfolio limits.
- Create: `src/polymarket_arb/sim/execution.py`
  Strict paired taker-fill simulator and failure classification.
- Create: `src/polymarket_arb/portfolio/ledger.py`
  Cash, locked capital, open lots, broken-pair exposure, and realized PnL tracking.
- Create: `src/polymarket_arb/portfolio/lifecycle.py`
  Default v1 realization rule: realized at modeled market resolution.
- Create: `src/polymarket_arb/engine.py`
  Orchestrates state updates, opportunity checks, sizing, simulation, and reporting hooks.
- Create: `src/polymarket_arb/reporting/writers.py`
  CSV and JSON outputs for summaries, trade logs, and rejected-opportunity logs.

### Tests And Fixtures

- Create: `tests/fixtures/gamma/market_binary.json`
  Minimal valid market metadata fixture.
- Create: `tests/fixtures/gamma/market_invalid.json`
  Fixture for non-binary or unusable market metadata.
- Create: `tests/fixtures/events/replay_sequence.jsonl`
  Deterministic normalized-event sequence for replay and engine tests.
- Create: `tests/unit/test_cli.py`
  CLI smoke tests.
- Create: `tests/unit/test_config.py`
  Config parsing tests.
- Create: `tests/unit/catalog/test_service.py`
  Market catalog resolution tests.
- Create: `tests/unit/recording/test_storage.py`
  Recorder storage round-trip tests.
- Create: `tests/unit/state/test_store.py`
  Market state freshness and pairing tests.
- Create: `tests/unit/strategy/test_opportunity.py`
  Net-cost and rejection tests.
- Create: `tests/unit/strategy/test_sizing.py`
  Paired-size limit tests.
- Create: `tests/unit/sim/test_execution.py`
  Strict paired fill and broken-pair classification tests.
- Create: `tests/unit/portfolio/test_ledger.py`
  Cash locking and realization tests.
- Create: `tests/integration/test_replay_runner.py`
  Replay adapter and engine integration tests.
- Create: `tests/integration/test_live_paper_runner.py`
  Live adapter to engine integration using fixture payloads.
- Create: `tests/acceptance/test_phase1_smoke.py`
  Acceptance scenarios from the spec.

## Task 1: Bootstrap The Python Project And CLI Shell

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `artifacts/.gitkeep`
- Create: `src/polymarket_arb/__init__.py`
- Create: `src/polymarket_arb/cli.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_cli_help_lists_core_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "catalog-refresh" in result.stdout
    assert "record-live" in result.stdout
    assert "run-replay" in result.stdout
    assert "run-paper" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing `app`.

- [ ] **Step 3: Write the minimal project skeleton**

```toml
[project]
name = "polymarket-arb"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27,<0.28",
  "pydantic>=2.8,<3",
  "PyYAML>=6.0,<7",
  "typer>=0.12,<0.13",
  "websockets>=13,<14",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.23,<0.24",
]

[project.scripts]
polymarket-arb = "polymarket_arb.cli:app"
```

```python
import typer

app = typer.Typer(no_args_is_help=True)


@app.command("catalog-refresh")
def catalog_refresh() -> None:
    """Refresh the curated market catalog."""


@app.command("record-live")
def record_live() -> None:
    """Record normalized live market events."""


@app.command("run-replay")
def run_replay() -> None:
    """Run replay mode on recorded data."""


@app.command("run-paper")
def run_paper() -> None:
    """Run live paper-trading mode."""
```

- [ ] **Step 4: Add repository hygiene**

```gitignore
.DS_Store
.pytest_cache/
.venv/
__pycache__/
.superpowers/
artifacts/*
!artifacts/.gitkeep
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore README.md artifacts/.gitkeep src/polymarket_arb/__init__.py src/polymarket_arb/cli.py tests/unit/test_cli.py
git commit -m "feat: bootstrap polymarket arb project"
```

## Task 2: Add Config Parsing And Stable Domain Models

**Files:**
- Create: `configs/markets.sample.yaml`
- Create: `src/polymarket_arb/config.py`
- Create: `src/polymarket_arb/domain/models.py`
- Create: `src/polymarket_arb/domain/events.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path

from polymarket_arb.config import load_settings


def test_load_settings_reads_allowlist_and_risk_caps(tmp_path: Path) -> None:
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(
        """
        venue: polymarket
        markets:
          - slug: will-btc-be-above-100k
            max_capital_usd: 50
        strategy:
          raw_alert_threshold: 0.99
          fee_rate: 0.01
          slippage_buffer: 0.005
          operational_buffer: 0.005
          stale_after_ms: 5000
        portfolio:
          starting_cash_usd: 500
          max_total_deployed_usd: 200
        """.strip()
    )

    settings = load_settings(config_path)

    assert settings.venue == "polymarket"
    assert settings.markets[0].slug == "will-btc-be-above-100k"
    assert settings.portfolio.starting_cash_usd == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL with missing `load_settings`.

- [ ] **Step 3: Implement the config and domain model layer**

```python
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


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
    markets: list[MarketSelection]
    strategy: StrategySettings
    portfolio: PortfolioSettings


def load_settings(path: Path) -> Settings:
    return Settings.model_validate(yaml.safe_load(path.read_text()))
```

```python
from pydantic import BaseModel


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


class Opportunity(BaseModel):
    market_id: str
    yes_ask: float
    no_ask: float
    estimated_net_cost: float
    paired_size: float
```

- [ ] **Step 4: Add normalized event types**

```python
from pydantic import BaseModel

from polymarket_arb.domain.models import BookLevel


class OrderBookEvent(BaseModel):
    market_id: str
    side: str
    asks: list[BookLevel]
    timestamp_ms: int
```

- [ ] **Step 5: Add a checked-in sample config**

```yaml
venue: polymarket
markets:
  - slug: will-btc-be-above-100k
    max_capital_usd: 50
strategy:
  raw_alert_threshold: 0.99
  fee_rate: 0.01
  slippage_buffer: 0.005
  operational_buffer: 0.005
  stale_after_ms: 5000
portfolio:
  starting_cash_usd: 500
  max_total_deployed_usd: 200
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add configs/markets.sample.yaml src/polymarket_arb/config.py src/polymarket_arb/domain/models.py src/polymarket_arb/domain/events.py tests/unit/test_config.py
git commit -m "feat: add config and domain models"
```

## Task 3: Implement Market Catalog Resolution From Gamma Metadata

**Files:**
- Create: `src/polymarket_arb/clients/gamma.py`
- Create: `src/polymarket_arb/catalog/service.py`
- Create: `tests/fixtures/gamma/market_binary.json`
- Create: `tests/fixtures/gamma/market_invalid.json`
- Test: `tests/unit/catalog/test_service.py`

- [ ] **Step 1: Write the failing catalog test**

```python
import json
from pathlib import Path

from polymarket_arb.catalog.service import build_catalog


def test_build_catalog_returns_binary_market_entry() -> None:
    payload = [json.loads(Path("tests/fixtures/gamma/market_binary.json").read_text())]

    catalog = build_catalog(payload, allowlist_caps={"will-btc-be-above-100k": 50.0})

    assert len(catalog) == 1
    assert catalog[0].slug == "will-btc-be-above-100k"
    assert catalog[0].yes_token_id
    assert catalog[0].no_token_id
    assert catalog[0].max_capital_usd == 50.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/catalog/test_service.py -v`
Expected: FAIL with missing `build_catalog`.

- [ ] **Step 3: Add Gamma metadata fixtures**

```json
{
  "id": "market-1",
  "slug": "will-btc-be-above-100k",
  "question": "Will BTC be above $100k on July 1?",
  "active": true,
  "closed": false,
  "outcomes": ["Yes", "No"],
  "clobTokenIds": ["yes-token", "no-token"],
  "feesEnabled": true
}
```

```json
{
  "id": "market-2",
  "slug": "multi-outcome-market",
  "active": true,
  "closed": false,
  "outcomes": ["A", "B", "C"],
  "clobTokenIds": ["a", "b", "c"],
  "feesEnabled": false
}
```

- [ ] **Step 4: Implement the catalog builder**

```python
from polymarket_arb.domain.models import MarketCatalogEntry


def build_catalog(markets: list[dict], allowlist_caps: dict[str, float]) -> list[MarketCatalogEntry]:
    entries: list[MarketCatalogEntry] = []
    for market in markets:
        slug = market.get("slug")
        if slug not in allowlist_caps:
            continue
        outcomes = market.get("outcomes", [])
        token_ids = market.get("clobTokenIds", [])
        if len(outcomes) != 2 or len(token_ids) != 2:
            continue
        if not market.get("active") or market.get("closed"):
            continue
        entries.append(
            MarketCatalogEntry(
                market_id=str(market["id"]),
                slug=slug,
                question=str(market.get("question", "")),
                yes_token_id=str(token_ids[0]),
                no_token_id=str(token_ids[1]),
                fees_enabled=bool(market.get("feesEnabled", False)),
                max_capital_usd=allowlist_caps[slug],
            )
        )
    return entries
```

- [ ] **Step 5: Add a small HTTP client wrapper**

```python
import httpx


class GammaClient:
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com") -> None:
        self._client = httpx.Client(base_url=base_url, timeout=10.0)

    def fetch_markets(self) -> list[dict]:
        response = self._client.get("/markets")
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/catalog/test_service.py tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/clients/gamma.py src/polymarket_arb/catalog/service.py tests/fixtures/gamma/market_binary.json tests/fixtures/gamma/market_invalid.json tests/unit/catalog/test_service.py
git commit -m "feat: add gamma market catalog loader"
```

## Task 4: Build Replay Artifact Storage And The Recorder Service

**Files:**
- Create: `src/polymarket_arb/recording/storage.py`
- Create: `src/polymarket_arb/recording/recorder.py`
- Test: `tests/unit/recording/test_storage.py`

- [ ] **Step 1: Write the failing storage round-trip test**

```python
import json
from pathlib import Path

from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.recording.storage import JsonlEventStore


def test_jsonl_event_store_writes_and_reads_orderbook_events(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    event = OrderBookEvent(
        market_id="market-1",
        side="YES",
        asks=[BookLevel(price=0.43, size=100)],
        timestamp_ms=1_700_000_000_000,
    )

    store.append(event)
    loaded = list(store.iter_events())

    assert loaded == [event]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/recording/test_storage.py -v`
Expected: FAIL with missing `JsonlEventStore`.

- [ ] **Step 3: Implement a deterministic event store**

```python
from pathlib import Path

from polymarket_arb.domain.events import OrderBookEvent


class JsonlEventStore:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._run_dir / "events.jsonl"
        self._catalog_path = self._run_dir / "catalog.json"

    def append(self, event: OrderBookEvent) -> None:
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def iter_events(self):
        for line in self._events_path.read_text().splitlines():
            yield OrderBookEvent.model_validate_json(line)

    def write_catalog(self, catalog: list[MarketCatalogEntry]) -> None:
        self._catalog_path.write_text(
            json.dumps([entry.model_dump() for entry in catalog], indent=2) + "\n"
        )
```

- [ ] **Step 4: Add a recorder service around the store**

```python
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.recording.storage import JsonlEventStore


class Recorder:
    def __init__(self, store: JsonlEventStore) -> None:
        self._store = store

    def start_run(self, catalog: list[MarketCatalogEntry]) -> None:
        self._store.write_catalog(catalog)

    def record(self, event: OrderBookEvent) -> None:
        self._store.append(event)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/recording/test_storage.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/recording/storage.py src/polymarket_arb/recording/recorder.py tests/unit/recording/test_storage.py
git commit -m "feat: add replay event storage"
```

## Task 5: Add Paired Market State Tracking And Replay Adapter

**Files:**
- Create: `src/polymarket_arb/state/store.py`
- Create: `src/polymarket_arb/adapters/replay.py`
- Create: `tests/fixtures/events/replay_sequence.jsonl`
- Test: `tests/unit/state/test_store.py`
- Test: `tests/integration/test_replay_runner.py`

- [ ] **Step 1: Write the failing market-state test**

```python
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.state.store import MarketStateStore


def test_market_state_store_tracks_yes_and_no_books() -> None:
    store = MarketStateStore(stale_after_ms=5_000)
    store.apply(
        OrderBookEvent(
            market_id="market-1",
            side="YES",
            asks=[BookLevel(price=0.43, size=50)],
            timestamp_ms=1_000,
        )
    )
    store.apply(
        OrderBookEvent(
            market_id="market-1",
            side="NO",
            asks=[BookLevel(price=0.54, size=50)],
            timestamp_ms=1_100,
        )
    )

    paired = store.get_paired_book("market-1", now_ms=1_200)

    assert paired.yes_asks[0].price == 0.43
    assert paired.no_asks[0].price == 0.54
    assert paired.is_fresh is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/state/test_store.py tests/integration/test_replay_runner.py -v`
Expected: FAIL with missing `MarketStateStore` and replay adapter.

- [ ] **Step 3: Implement paired market state**

```python
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
```

- [ ] **Step 4: Implement the replay adapter**

```python
from polymarket_arb.recording.storage import JsonlEventStore


class ReplayAdapter:
    def __init__(self, store: JsonlEventStore) -> None:
        self._store = store

    def iter_events(self):
        yield from self._store.iter_events()
```

- [ ] **Step 5: Add a replay integration test**

```python
from pathlib import Path

from polymarket_arb.adapters.replay import ReplayAdapter
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.recording.storage import JsonlEventStore


def test_replay_adapter_yields_events_in_recorded_order(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    first = OrderBookEvent(
        market_id="market-1",
        side="YES",
        asks=[BookLevel(price=0.43, size=10)],
        timestamp_ms=1000,
    )
    second = OrderBookEvent(
        market_id="market-1",
        side="NO",
        asks=[BookLevel(price=0.54, size=10)],
        timestamp_ms=1001,
    )
    store.append(first)
    store.append(second)

    replayed = list(ReplayAdapter(store).iter_events())

    assert replayed == [first, second]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/state/test_store.py tests/integration/test_replay_runner.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/state/store.py src/polymarket_arb/adapters/replay.py tests/fixtures/events/replay_sequence.jsonl tests/unit/state/test_store.py tests/integration/test_replay_runner.py
git commit -m "feat: add paired market state and replay adapter"
```

## Task 6: Implement Opportunity Math And Position Sizing

**Files:**
- Create: `src/polymarket_arb/strategy/opportunity.py`
- Create: `src/polymarket_arb/strategy/sizing.py`
- Test: `tests/unit/strategy/test_opportunity.py`
- Test: `tests/unit/strategy/test_sizing.py`

- [ ] **Step 1: Write the failing opportunity test**

```python
from polymarket_arb.strategy.opportunity import evaluate_opportunity


def test_evaluate_opportunity_rejects_edge_consumed_by_costs() -> None:
    result = evaluate_opportunity(
        yes_ask=0.43,
        no_ask=0.54,
        raw_alert_threshold=0.99,
        fee_rate=0.01,
        slippage_buffer=0.01,
        operational_buffer=0.005,
    )

    assert result.accepted is False
    assert result.rejection_reason == "threshold_not_met_after_costs"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/strategy/test_opportunity.py tests/unit/strategy/test_sizing.py -v`
Expected: FAIL with missing strategy functions.

- [ ] **Step 3: Implement net-cost evaluation**

```python
from dataclasses import dataclass


@dataclass
class OpportunityDecision:
    accepted: bool
    estimated_net_cost: float
    rejection_reason: str | None


def evaluate_opportunity(
    *,
    yes_ask: float,
    no_ask: float,
    raw_alert_threshold: float,
    fee_rate: float,
    slippage_buffer: float,
    operational_buffer: float,
) -> OpportunityDecision:
    gross = yes_ask + no_ask
    if gross >= raw_alert_threshold:
        return OpportunityDecision(False, gross, "raw_threshold_not_met")
    estimated_net_cost = gross + fee_rate + slippage_buffer + operational_buffer
    if estimated_net_cost >= 1.0:
        return OpportunityDecision(False, estimated_net_cost, "threshold_not_met_after_costs")
    return OpportunityDecision(True, estimated_net_cost, None)
```

- [ ] **Step 4: Implement paired-size calculation**

```python
def compute_paired_size(
    *,
    yes_size: float,
    no_size: float,
    available_cash: float,
    per_market_cap_usd: float,
    remaining_deployable_usd: float,
    estimated_net_cost: float,
) -> float:
    paired_depth = min(yes_size, no_size)
    cash_limited = available_cash / estimated_net_cost
    market_cap_limited = per_market_cap_usd / estimated_net_cost
    portfolio_limited = remaining_deployable_usd / estimated_net_cost
    return max(0.0, min(paired_depth, cash_limited, market_cap_limited, portfolio_limited))
```

- [ ] **Step 5: Add tests for accepted opportunities and cap-limited size**

```python
def test_compute_paired_size_respects_smallest_limit() -> None:
    result = compute_paired_size(
        yes_size=100,
        no_size=80,
        available_cash=20,
        per_market_cap_usd=100,
        remaining_deployable_usd=100,
        estimated_net_cost=0.50,
    )
    assert result == 40
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/strategy/test_opportunity.py tests/unit/strategy/test_sizing.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/strategy/opportunity.py src/polymarket_arb/strategy/sizing.py tests/unit/strategy/test_opportunity.py tests/unit/strategy/test_sizing.py
git commit -m "feat: add opportunity math and paired sizing"
```

## Task 7: Add Strict Paired Execution, Portfolio Tracking, And Resolution Lifecycle

**Files:**
- Create: `src/polymarket_arb/sim/execution.py`
- Create: `src/polymarket_arb/portfolio/ledger.py`
- Create: `src/polymarket_arb/portfolio/lifecycle.py`
- Test: `tests/unit/sim/test_execution.py`
- Test: `tests/unit/portfolio/test_ledger.py`

- [ ] **Step 1: Write the failing execution test**

```python
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.execution import simulate_strict_pair_fill


def test_simulate_strict_pair_fill_succeeds_when_both_books_have_depth() -> None:
    result = simulate_strict_pair_fill(
        yes_asks=[BookLevel(price=0.43, size=10)],
        no_asks=[BookLevel(price=0.54, size=10)],
        target_size=5,
    )

    assert result.status == "filled"
    assert result.filled_size == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/sim/test_execution.py tests/unit/portfolio/test_ledger.py -v`
Expected: FAIL with missing simulator and ledger.

- [ ] **Step 3: Implement strict paired execution**

```python
from dataclasses import dataclass


@dataclass
class FillResult:
    status: str
    filled_size: float
    total_cost: float


def simulate_strict_pair_fill(*, yes_asks, no_asks, target_size: float) -> FillResult:
    def consume_cost(levels, size):
        remaining = size
        total = 0.0
        for level in levels:
            take = min(level.size, remaining)
            total += take * level.price
            remaining -= take
            if remaining == 0:
                return total
        return None

    yes_available = sum(level.size for level in yes_asks)
    no_available = sum(level.size for level in no_asks)
    if min(yes_available, no_available) < target_size:
        return FillResult("broken_pair", 0.0, 0.0)
    yes_cost = consume_cost(yes_asks, target_size)
    no_cost = consume_cost(no_asks, target_size)
    return FillResult("filled", target_size, yes_cost + no_cost)
```

- [ ] **Step 4: Implement the portfolio ledger**

```python
from dataclasses import dataclass


@dataclass
class PortfolioLedger:
    starting_cash_usd: float
    free_cash_usd: float
    locked_cost_basis_usd: float = 0.0
    realized_pnl_usd: float = 0.0

    def open_pair(self, total_cost: float) -> None:
        self.free_cash_usd -= total_cost
        self.locked_cost_basis_usd += total_cost

    def resolve_pair(self, *, total_cost: float, payout: float) -> None:
        self.locked_cost_basis_usd -= total_cost
        self.free_cash_usd += payout
        self.realized_pnl_usd += payout - total_cost
```

- [ ] **Step 5: Add a lifecycle test for modeled resolution**

```python
def test_portfolio_ledger_realizes_profit_on_resolution() -> None:
    ledger = PortfolioLedger(starting_cash_usd=500, free_cash_usd=500)
    ledger.open_pair(total_cost=97)
    ledger.resolve_pair(total_cost=97, payout=100)
    assert ledger.free_cash_usd == 503
    assert ledger.realized_pnl_usd == 3
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/sim/test_execution.py tests/unit/portfolio/test_ledger.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/sim/execution.py src/polymarket_arb/portfolio/ledger.py src/polymarket_arb/portfolio/lifecycle.py tests/unit/sim/test_execution.py tests/unit/portfolio/test_ledger.py
git commit -m "feat: add strict pair simulation and ledger"
```

## Task 8: Wire The Shared Engine For Replay Decisions

**Files:**
- Create: `src/polymarket_arb/engine.py`
- Modify: `src/polymarket_arb/state/store.py`
- Modify: `src/polymarket_arb/strategy/opportunity.py`
- Modify: `src/polymarket_arb/strategy/sizing.py`
- Test: `tests/integration/test_replay_runner.py`

- [ ] **Step 1: Write the failing replay-engine test**

```python
from polymarket_arb.engine import TradingEngine


def test_trading_engine_emits_trade_for_executable_pair(replay_events) -> None:
    engine = TradingEngine.from_defaults(starting_cash_usd=500)
    results = [engine.on_event(event) for event in replay_events]

    assert any(result and result.decision == "trade" for result in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_replay_runner.py -v`
Expected: FAIL with missing `TradingEngine`.

- [ ] **Step 3: Implement the shared engine**

```python
from dataclasses import dataclass


@dataclass
class EngineOutcome:
    decision: str
    fill: object | None = None
    rejection_reason: str | None = None


class TradingEngine:
    def __init__(self, state_store, ledger, settings, market_caps_by_id) -> None:
        self._state_store = state_store
        self._ledger = ledger
        self._settings = settings
        self._market_caps_by_id = market_caps_by_id

    @classmethod
    def from_defaults(cls, *, starting_cash_usd: float, per_market_cap_usd: float = 50.0, stale_after_ms: int = 5_000):
        settings = type(
            "EngineSettings",
            (),
            {
                "strategy": type(
                    "Strategy",
                    (),
                    {"raw_alert_threshold": 0.99, "fee_rate": 0.01, "slippage_buffer": 0.005, "operational_buffer": 0.005},
                )(),
                "portfolio": type("Portfolio", (), {"max_total_deployed_usd": starting_cash_usd})(),
            },
        )()
        return cls(
            state_store=MarketStateStore(stale_after_ms=stale_after_ms),
            ledger=PortfolioLedger(starting_cash_usd=starting_cash_usd, free_cash_usd=starting_cash_usd),
            settings=settings,
            market_caps_by_id={"market-1": per_market_cap_usd},
        )

    def on_event(self, event):
        self._state_store.apply(event)
        try:
            paired = self._state_store.get_paired_book(event.market_id, event.timestamp_ms)
        except ValueError as exc:
            return EngineOutcome("reject", rejection_reason=str(exc))
        if not paired.yes_asks or not paired.no_asks:
            return EngineOutcome("reject", rejection_reason="missing_paired_book")
        decision = evaluate_opportunity(
            yes_ask=paired.yes_asks[0].price,
            no_ask=paired.no_asks[0].price,
            raw_alert_threshold=self._settings.strategy.raw_alert_threshold,
            fee_rate=self._settings.strategy.fee_rate,
            slippage_buffer=self._settings.strategy.slippage_buffer,
            operational_buffer=self._settings.strategy.operational_buffer,
        )
        if not decision.accepted:
            return EngineOutcome("reject", rejection_reason=decision.rejection_reason)
        size = compute_paired_size(
            yes_size=paired.yes_asks[0].size,
            no_size=paired.no_asks[0].size,
            available_cash=self._ledger.free_cash_usd,
            per_market_cap_usd=self._market_caps_by_id[event.market_id],
            remaining_deployable_usd=self._settings.portfolio.max_total_deployed_usd - self._ledger.locked_cost_basis_usd,
            estimated_net_cost=decision.estimated_net_cost,
        )
        if size <= 0:
            return EngineOutcome("reject", rejection_reason="size_limited_to_zero")
        fill = simulate_strict_pair_fill(
            yes_asks=paired.yes_asks,
            no_asks=paired.no_asks,
            target_size=size,
        )
        if fill.status != "filled":
            return EngineOutcome("reject", rejection_reason="broken_pair_execution")
        self._ledger.open_pair(fill.total_cost)
        return EngineOutcome("trade", fill=fill)

    def run(self, events):
        trade_count = 0
        rejection_count = 0
        for event in events:
            outcome = self.on_event(event)
            if not outcome:
                continue
            if outcome.decision == "trade":
                trade_count += 1
            else:
                rejection_count += 1
        return {
            "trades": trade_count,
            "rejections": rejection_count,
            "realized_pnl_usd": self._ledger.realized_pnl_usd,
        }
```

- [ ] **Step 4: Expand replay integration coverage**

```python
def test_trading_engine_rejects_stale_books(replay_events) -> None:
    engine = TradingEngine.from_defaults(starting_cash_usd=500, stale_after_ms=1)
    results = [engine.on_event(event) for event in replay_events]
    assert all(result and result.decision == "reject" for result in results)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/integration/test_replay_runner.py tests/unit/state/test_store.py tests/unit/strategy/test_opportunity.py tests/unit/sim/test_execution.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/engine.py src/polymarket_arb/state/store.py src/polymarket_arb/strategy/opportunity.py src/polymarket_arb/strategy/sizing.py tests/integration/test_replay_runner.py
git commit -m "feat: wire shared replay trading engine"
```

## Task 9: Add The Live Adapter And Paper-Trading Runner

**Files:**
- Create: `src/polymarket_arb/clients/clob.py`
- Create: `src/polymarket_arb/adapters/live.py`
- Test: `tests/integration/test_live_paper_runner.py`

- [ ] **Step 1: Write the failing live-adapter test**

```python
from polymarket_arb.adapters.live import normalize_orderbook_payload


def test_normalize_orderbook_payload_maps_yes_and_no_books() -> None:
    payload = {
        "market": "market-1",
        "side": "YES",
        "asks": [["0.43", "10"]],
        "timestamp": 1_700_000_000_000,
    }

    event = normalize_orderbook_payload(payload)

    assert event.market_id == "market-1"
    assert event.asks[0].price == 0.43
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_live_paper_runner.py -v`
Expected: FAIL with missing live adapter functions.

- [ ] **Step 3: Implement payload normalization**

```python
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel


def normalize_orderbook_payload(payload: dict) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=str(payload["market"]),
        side=str(payload["side"]),
        asks=[BookLevel(price=float(price), size=float(size)) for price, size in payload["asks"]],
        timestamp_ms=int(payload["timestamp"]),
    )
```

- [ ] **Step 4: Add a paper-runner integration test**

```python
def test_live_adapter_events_drive_same_engine_decisions_as_replay() -> None:
    from polymarket_arb.engine import TradingEngine

    payloads = [
        {"market": "market-1", "side": "YES", "asks": [["0.43", "10"]], "timestamp": 1000},
        {"market": "market-1", "side": "NO", "asks": [["0.54", "10"]], "timestamp": 1001},
    ]

    engine = TradingEngine.from_defaults(starting_cash_usd=500)
    decisions = [engine.on_event(normalize_orderbook_payload(payload)) for payload in payloads]

    assert any(decision and decision.decision == "trade" for decision in decisions)
```

- [ ] **Step 5: Add a thin async client wrapper**

```python
import websockets


class ClobWebSocketClient:
    async def subscribe(self, url: str):
        async with websockets.connect(url) as websocket:
            async for message in websocket:
                yield message
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/integration/test_live_paper_runner.py tests/integration/test_replay_runner.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/clients/clob.py src/polymarket_arb/adapters/live.py tests/integration/test_live_paper_runner.py
git commit -m "feat: add live adapter and paper runner"
```

## Task 10: Add Reporting Outputs And End-To-End CLI Flows

**Files:**
- Create: `src/polymarket_arb/reporting/writers.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/acceptance/test_phase1_smoke.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing reporting test**

```python
from pathlib import Path

from polymarket_arb.reporting.writers import write_run_summary


def test_write_run_summary_creates_json_file(tmp_path: Path) -> None:
    output = write_run_summary(
        tmp_path,
        {"trades": 1, "rejections": 2, "realized_pnl_usd": 3.0},
    )
    assert output.exists()
    assert "realized_pnl_usd" in output.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/acceptance/test_phase1_smoke.py -v`
Expected: FAIL with missing reporting utilities or CLI flow.

- [ ] **Step 3: Implement report writers**

```python
import json
from pathlib import Path


def write_run_summary(output_dir: Path, summary: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary_path
```

- [ ] **Step 4: Wire real CLI commands for replay and paper mode**

```python
@app.command("run-replay")
def run_replay(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    output_dir: Path = typer.Option(..., "--output-dir"),
) -> None:
    settings = load_settings(config_path)
    store = JsonlEventStore(run_dir)
    adapter = ReplayAdapter(store)
    catalog = load_recorded_catalog(run_dir / "catalog.json")
    engine = TradingEngine.from_settings(settings, catalog)
    summary = engine.run(adapter.iter_events())
    write_run_summary(output_dir, summary)


@app.command("record-live")
def record_live(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    duration_seconds: int = typer.Option(60, "--duration-seconds"),
) -> None:
    settings = load_settings(config_path)
    adapter = LiveAdapter.from_settings(settings)
    store = JsonlEventStore(run_dir)
    catalog = refresh_catalog(settings)
    recorder = Recorder(store)
    recorder.start_run(catalog)
    for event in adapter.iter_events(limit_seconds=duration_seconds):
        recorder.record(event)


@app.command("run-paper")
def run_paper(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    duration_seconds: int = typer.Option(60, "--duration-seconds"),
) -> None:
    settings = load_settings(config_path)
    adapter = LiveAdapter.from_settings(settings)
    catalog = refresh_catalog(settings)
    engine = TradingEngine.from_settings(settings, catalog)
    summary = engine.run(adapter.iter_events(limit_seconds=duration_seconds))
    write_run_summary(output_dir, summary)
```

- [ ] **Step 5: Add an acceptance smoke test**

```python
def test_run_replay_command_writes_summary(tmp_path: Path) -> None:
    from pathlib import Path

    from typer.testing import CliRunner

    from polymarket_arb.cli import app
    from polymarket_arb.domain.events import OrderBookEvent
    from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
    from polymarket_arb.recording.storage import JsonlEventStore

    runner = CliRunner()
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text())

    store = JsonlEventStore(run_dir)
    store.write_catalog(
        [
            MarketCatalogEntry(
                market_id="market-1",
                slug="will-btc-be-above-100k",
                question="Will BTC be above $100k?",
                yes_token_id="yes-token",
                no_token_id="no-token",
                fees_enabled=True,
                max_capital_usd=50,
            )
        ]
    )
    store.append(OrderBookEvent(market_id="market-1", side="YES", asks=[BookLevel(price=0.43, size=10)], timestamp_ms=1000))
    store.append(OrderBookEvent(market_id="market-1", side="NO", asks=[BookLevel(price=0.54, size=10)], timestamp_ms=1001))

    result = runner.invoke(
        app,
        [
            "run-replay",
            "--config-path",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.json").exists()
```

- [ ] **Step 6: Update `README.md` with developer commands**

```markdown
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -v
polymarket-arb run-replay --config-path configs/markets.sample.yaml --run-dir artifacts/demo-run --output-dir artifacts/demo-report
```

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/polymarket_arb/reporting/writers.py src/polymarket_arb/cli.py tests/acceptance/test_phase1_smoke.py README.md
git commit -m "feat: add reporting and cli flows"
```

## Task 11: Verification And Cleanup

**Files:**
- Modify: `README.md`
- Modify: `configs/markets.sample.yaml`

- [ ] **Step 1: Run a clean-room install test**

Run: `python -m pip install -e .[dev]`
Expected: successful editable install with dev dependencies.

- [ ] **Step 2: Run the full verification commands**

Run: `pytest -v`
Expected: PASS

Run: `polymarket-arb --help`
Expected: lists the four core commands.

Run: `polymarket-arb run-replay --help`
Expected: shows config, run-dir, and output-dir options.

- [ ] **Step 3: Update docs for any mismatches discovered during verification**

```markdown
If any command flags or setup steps differ from the plan, update `README.md` and `configs/markets.sample.yaml` now instead of leaving drift for later.
```

- [ ] **Step 4: Commit**

```bash
git add README.md configs/markets.sample.yaml
git commit -m "docs: finalize v1 setup and verification notes"
```

## Notes For The Implementer

- Keep the domain models stable and small. Do not let HTTP payload shapes leak across the package.
- Replay fidelity matters more than feature count. If a shortcut weakens the recorded-event model, reject it.
- Do not claim "risk-free" behavior anywhere in code or docs. Use terms like `full-set arbitrage`, `paired position`, and `modeled profit`.
- Stick to strict paired execution in v1. Broken-pair handling should be logged and classified, not optimized away.
- Prefer fixtures over live network calls in tests.
- If live Polymarket payloads differ from fixture assumptions, update the fixtures and normalization layer without changing core engine contracts.
