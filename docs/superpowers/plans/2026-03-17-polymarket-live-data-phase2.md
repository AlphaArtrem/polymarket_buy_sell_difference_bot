# Polymarket Live Data Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current synthetic catalog/live-data skeleton with real public Polymarket market-data integration so `catalog-refresh`, `record-live`, and `run-paper` operate on actual curated markets.

**Architecture:** Keep the engine, replay path, and cost/sizing logic unchanged. Focus this phase on the data boundary: Gamma market discovery, CLOB public orderbook reads, a lightweight live adapter that emits real normalized events, and CLI/reporting behavior that fails clearly when replay input is missing or empty.

**Tech Stack:** Python 3.9+, `typer`, `httpx`, `PyYAML`, `pydantic`, `pytest`, `pytest-asyncio`

---

## Scope Check

This plan intentionally stops at real public market-data ingestion. It does not include:

- authenticated order placement
- `py-clob-client` integration
- WebSocket-based low-latency execution tuning
- merge execution
- live-money trading

This phase is about turning the current working skeleton into a real public-data pipeline while keeping the hot path lightweight.

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add explicit public API settings, polling interval, and optional output path for refreshed catalog artifacts.
- Modify: `src/polymarket_arb/domain/models.py`
  Expand catalog and state models with any fields required to map real Gamma/CLOB responses cleanly.
- Modify: `src/polymarket_arb/clients/gamma.py`
  Add real curated-market fetch methods using slugs and usable market filtering.
- Modify: `src/polymarket_arb/clients/clob.py`
  Add public orderbook fetch methods for token IDs and lightweight polling helpers.
- Modify: `src/polymarket_arb/catalog/service.py`
  Turn it into a real catalog refresh layer that combines allowlist config with fetched Gamma metadata.
- Modify: `src/polymarket_arb/adapters/live.py`
  Replace the empty `LiveAdapter` with a polling-based adapter that emits real `OrderBookEvent` instances.
- Modify: `src/polymarket_arb/recording/storage.py`
  Add explicit read helpers and missing-artifact checks for replay inputs.
- Modify: `src/polymarket_arb/cli.py`
  Wire `catalog-refresh`, `record-live`, and `run-paper` to the real clients and emit clear user-facing errors.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Add small helpers for writing refreshed catalog snapshots or run metadata if needed.
- Modify: `README.md`
  Update commands to reflect real public-data behavior and prerequisites.

### Files To Create

- Create: `tests/fixtures/gamma/markets_list.json`
  Realistic Gamma list response fixture containing at least one valid curated binary market and one invalid market.
- Create: `tests/fixtures/clob/book_yes.json`
  Realistic public orderbook fixture for a `YES` token.
- Create: `tests/fixtures/clob/book_no.json`
  Realistic public orderbook fixture for a `NO` token.
- Create: `tests/unit/clients/test_gamma.py`
  Tests for Gamma market fetch and filtering logic.
- Create: `tests/unit/clients/test_clob.py`
  Tests for public orderbook fetch and normalization logic.
- Create: `tests/unit/catalog/test_refresh.py`
  Tests for real catalog refresh combining settings and Gamma results.
- Create: `tests/integration/test_record_live_cli.py`
  End-to-end CLI test for `record-live` using mocked Gamma/CLOB clients.
- Create: `tests/integration/test_run_paper_cli.py`
  End-to-end CLI test for `run-paper` using mocked public data.
- Create: `tests/unit/test_replay_errors.py`
  Tests that `run-replay` fails loudly when `catalog.json` or `events.jsonl` is missing.

## Task 1: Add Real Public API Settings And Catalog Models

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Modify: `src/polymarket_arb/domain/models.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing config test for API settings**

```python
from pathlib import Path
from textwrap import dedent

from polymarket_arb.config import load_settings


def test_load_settings_reads_public_api_endpoints_and_poll_interval(tmp_path: Path) -> None:
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
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
            """
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.api.gamma_base_url == "https://gamma-api.polymarket.com"
    assert settings.api.poll_interval_ms == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py -v`
Expected: FAIL because `api` settings do not exist yet.

- [ ] **Step 3: Add minimal API settings and catalog fields**

```python
class ApiSettings(BaseModel):
    gamma_base_url: str
    clob_base_url: str
    poll_interval_ms: int = Field(gt=0)


class Settings(BaseModel):
    venue: str
    api: ApiSettings
    markets: list[MarketSelection]
    strategy: StrategySettings
    portfolio: PortfolioSettings
```

```python
class MarketCatalogEntry(BaseModel):
    market_id: str
    slug: str
    question: str
    yes_token_id: str
    no_token_id: str
    fees_enabled: bool
    max_capital_usd: float
    active: bool = True
```

- [ ] **Step 4: Update `configs/markets.sample.yaml` in the same change**

```yaml
api:
  gamma_base_url: https://gamma-api.polymarket.com
  clob_base_url: https://clob.polymarket.com
  poll_interval_ms: 500
```

- [ ] **Step 5: Run config tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/config.py src/polymarket_arb/domain/models.py configs/markets.sample.yaml tests/unit/test_config.py
git commit -m "feat: add public api settings"
```

## Task 2: Implement Real Gamma Catalog Refresh

**Files:**
- Modify: `src/polymarket_arb/clients/gamma.py`
- Modify: `src/polymarket_arb/catalog/service.py`
- Create: `tests/fixtures/gamma/markets_list.json`
- Create: `tests/unit/clients/test_gamma.py`
- Create: `tests/unit/catalog/test_refresh.py`

- [ ] **Step 1: Write the failing Gamma client test**

```python
import json
from pathlib import Path

from polymarket_arb.catalog.service import refresh_catalog


def test_refresh_catalog_filters_gamma_results_to_curated_binary_markets() -> None:
    payload = json.loads(Path("tests/fixtures/gamma/markets_list.json").read_text())

    catalog = refresh_catalog(
        gamma_payload=payload,
        allowlist_caps={"will-btc-be-above-100k": 50.0},
    )

    assert len(catalog) == 1
    assert catalog[0].slug == "will-btc-be-above-100k"
    assert catalog[0].market_id != "market-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_gamma.py tests/unit/catalog/test_refresh.py -v`
Expected: FAIL because `refresh_catalog` does not exist.

- [ ] **Step 3: Add realistic Gamma fixture**

```json
[
  {
    "id": "0xabc",
    "slug": "will-btc-be-above-100k",
    "question": "Will BTC be above $100k?",
    "active": true,
    "closed": false,
    "outcomes": ["Yes", "No"],
    "clobTokenIds": ["yes-token-abc", "no-token-abc"],
    "feesEnabled": true
  },
  {
    "id": "0xdef",
    "slug": "multi-outcome-market",
    "active": true,
    "closed": false,
    "outcomes": ["A", "B", "C"],
    "clobTokenIds": ["a", "b", "c"],
    "feesEnabled": false
  }
]
```

- [ ] **Step 4: Implement refresh logic**

```python
def refresh_catalog(
    *, gamma_payload: list[dict], allowlist_caps: dict[str, float]
) -> list[MarketCatalogEntry]:
    entries = []
    for market in gamma_payload:
        slug = market.get("slug")
        if slug not in allowlist_caps:
            continue
        if not market.get("active") or market.get("closed"):
            continue
        outcomes = market.get("outcomes", [])
        token_ids = market.get("clobTokenIds", [])
        if len(outcomes) != 2 or len(token_ids) != 2:
            continue
        entries.append(
            MarketCatalogEntry(
                market_id=str(market["id"]),
                slug=str(slug),
                question=str(market.get("question", "")),
                yes_token_id=str(token_ids[0]),
                no_token_id=str(token_ids[1]),
                fees_enabled=bool(market.get("feesEnabled", False)),
                max_capital_usd=allowlist_caps[slug],
            )
        )
    return entries
```

- [ ] **Step 5: Add real HTTP fetch method**

```python
class GammaClient:
    def fetch_markets(self) -> list[dict]:
        response = self._client.get("/markets")
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_gamma.py tests/unit/catalog/test_refresh.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/clients/gamma.py src/polymarket_arb/catalog/service.py tests/fixtures/gamma/markets_list.json tests/unit/clients/test_gamma.py tests/unit/catalog/test_refresh.py
git commit -m "feat: add real gamma catalog refresh"
```

## Task 3: Implement Real Public CLOB Orderbook Reads

**Files:**
- Modify: `src/polymarket_arb/clients/clob.py`
- Modify: `src/polymarket_arb/adapters/live.py`
- Create: `tests/fixtures/clob/book_yes.json`
- Create: `tests/fixtures/clob/book_no.json`
- Create: `tests/unit/clients/test_clob.py`

- [ ] **Step 1: Write the failing CLOB client test**

```python
import json
from pathlib import Path

from polymarket_arb.adapters.live import normalize_orderbook_payload


def test_normalize_real_clob_book_payload() -> None:
    payload = json.loads(Path("tests/fixtures/clob/book_yes.json").read_text())

    event = normalize_orderbook_payload(payload)

    assert event.market_id == "0xabc"
    assert event.side == "YES"
    assert event.asks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob.py tests/integration/test_live_paper_runner.py -v`
Expected: FAIL because fixture shape and normalizer no longer match.

- [ ] **Step 3: Add realistic public book fixtures**

```json
{
  "market": "0xabc",
  "side": "YES",
  "asks": [["0.43", "15"], ["0.44", "20"]],
  "timestamp": 1700000000000
}
```

```json
{
  "market": "0xabc",
  "side": "NO",
  "asks": [["0.54", "15"], ["0.55", "20"]],
  "timestamp": 1700000000001
}
```

- [ ] **Step 4: Implement orderbook fetch helper**

```python
class ClobClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=10.0)

    def fetch_book(self, token_id: str) -> dict:
        response = self._client.get("/book", params={"token_id": token_id})
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 5: Keep live normalization thin**

```python
def normalize_orderbook_payload(payload: dict[str, Any]) -> OrderBookEvent:
    return OrderBookEvent(
        market_id=str(payload["market"]),
        side=str(payload["side"]).upper(),
        asks=[BookLevel(price=float(price), size=float(size)) for price, size in payload["asks"]],
        timestamp_ms=int(payload["timestamp"]),
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob.py tests/integration/test_live_paper_runner.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/clients/clob.py src/polymarket_arb/adapters/live.py tests/fixtures/clob/book_yes.json tests/fixtures/clob/book_no.json tests/unit/clients/test_clob.py tests/integration/test_live_paper_runner.py
git commit -m "feat: add public clob orderbook reads"
```

## Task 4: Replace The Empty Live Adapter With Real Polling

**Files:**
- Modify: `src/polymarket_arb/adapters/live.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/integration/test_record_live_cli.py`
- Create: `tests/integration/test_run_paper_cli.py`

- [ ] **Step 1: Write the failing `record-live` integration test**

```python
from pathlib import Path

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_record_live_writes_catalog_and_events_from_real_clients(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text())
    run_dir = tmp_path / "run"

    # monkeypatch GammaClient.fetch_markets and ClobClient.fetch_book
    result = runner.invoke(
        app,
        ["record-live", "--config-path", str(config_path), "--run-dir", str(run_dir), "--duration-seconds", "1"],
    )

    assert result.exit_code == 0
    assert (run_dir / "catalog.json").exists()
    assert (run_dir / "events.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_record_live_cli.py tests/integration/test_run_paper_cli.py -v`
Expected: FAIL because the adapter still emits no events from real clients.

- [ ] **Step 3: Implement polling-based live adapter**

```python
class LiveAdapter:
    def __init__(self, *, catalog, clob_client, poll_interval_ms: int) -> None:
        self._catalog = catalog
        self._clob_client = clob_client
        self._poll_interval_ms = poll_interval_ms

    @classmethod
    def from_settings(cls, settings, catalog, clob_client):
        return cls(catalog=catalog, clob_client=clob_client, poll_interval_ms=settings.api.poll_interval_ms)

    def iter_events(self, limit_seconds: int = 60):
        deadline = time.monotonic() + limit_seconds
        while time.monotonic() < deadline:
            now_ms = int(time.time() * 1000)
            for market in self._catalog:
                yield normalize_orderbook_payload(
                    self._clob_client.fetch_book(market.yes_token_id) | {"market": market.market_id, "side": "YES", "timestamp": now_ms}
                )
                yield normalize_orderbook_payload(
                    self._clob_client.fetch_book(market.no_token_id) | {"market": market.market_id, "side": "NO", "timestamp": now_ms}
                )
            time.sleep(self._poll_interval_ms / 1000)
```

- [ ] **Step 4: Wire CLI commands to real clients**

```python
def catalog_refresh(...):
    settings = load_settings(config_path)
    gamma_client = GammaClient(base_url=settings.api.gamma_base_url)
    catalog = refresh_catalog(gamma_payload=gamma_client.fetch_markets(), allowlist_caps={m.slug: m.max_capital_usd for m in settings.markets})
    JsonlEventStore(output_dir).write_catalog(catalog)
```

```python
def record_live(...):
    settings = load_settings(config_path)
    gamma_client = GammaClient(base_url=settings.api.gamma_base_url)
    clob_client = ClobClient(base_url=settings.api.clob_base_url)
    catalog = refresh_catalog(...)
    adapter = LiveAdapter.from_settings(settings, catalog, clob_client)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_record_live_cli.py tests/integration/test_run_paper_cli.py tests/integration/test_live_paper_runner.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/adapters/live.py src/polymarket_arb/cli.py tests/integration/test_record_live_cli.py tests/integration/test_run_paper_cli.py tests/integration/test_live_paper_runner.py
git commit -m "feat: connect live adapter to real public market data"
```

## Task 5: Make Replay And CLI Errors Explicit

**Files:**
- Modify: `src/polymarket_arb/recording/storage.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/unit/test_replay_errors.py`

- [ ] **Step 1: Write the failing replay-error test**

```python
from pathlib import Path

import pytest

from polymarket_arb.recording.storage import JsonlEventStore


def test_read_catalog_raises_when_catalog_missing(tmp_path: Path) -> None:
    store = JsonlEventStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read_catalog(required=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_replay_errors.py -v`
Expected: FAIL because missing artifacts are silently treated as empty inputs.

- [ ] **Step 3: Add explicit required reads**

```python
def read_catalog(self, required: bool = False) -> list[MarketCatalogEntry]:
    if not self._catalog_path.exists():
        if required:
            raise FileNotFoundError(f"Missing replay catalog: {self._catalog_path}")
        return []
```

```python
def iter_events(self, required: bool = False):
    if not self._events_path.exists():
        if required:
            raise FileNotFoundError(f"Missing replay events: {self._events_path}")
        return []
```

- [ ] **Step 4: Surface clean CLI errors**

```python
try:
    catalog = store.read_catalog(required=True)
    events = adapter.iter_events(required=True)
except FileNotFoundError as exc:
    raise typer.BadParameter(str(exc))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_replay_errors.py tests/acceptance/test_phase1_smoke.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/recording/storage.py src/polymarket_arb/cli.py tests/unit/test_replay_errors.py tests/acceptance/test_phase1_smoke.py
git commit -m "feat: add explicit replay input errors"
```

## Task 6: Update Documentation And Verify The Real Public-Data Slice

**Files:**
- Modify: `README.md`
- Modify: `configs/markets.sample.yaml`

- [ ] **Step 1: Update README commands**

```markdown
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli catalog-refresh --config-path configs/markets.sample.yaml --output-dir artifacts/catalog
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli record-live --config-path configs/markets.sample.yaml --run-dir artifacts/live-capture --duration-seconds 60
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --config-path configs/markets.sample.yaml --output-dir artifacts/paper-report --duration-seconds 60
```

- [ ] **Step 2: Run the full test suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 3: Run CLI verification commands**

Run: `PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli --help`
Expected: lists `catalog-refresh`, `record-live`, `run-replay`, and `run-paper`

Run: `PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli record-live --help`
Expected: shows config, run-dir, and duration options

Run: `PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --help`
Expected: shows config, output-dir, and duration options

- [ ] **Step 4: Commit**

```bash
git add README.md configs/markets.sample.yaml
git commit -m "docs: finalize live data phase 2 commands"
```

## Notes For The Implementer

- Keep the engine unchanged unless a real data shape forces a specific contract update.
- Avoid `py-clob-client` in this phase; the user explicitly prefers a lighter-weight hot path.
- Use fixture-driven tests for Gamma and CLOB payloads before touching live network behavior.
- Prefer polling first if it keeps this slice shippable. WebSocket speed improvements can be a separate plan once public polling works.
- Do not silently swallow missing replay input again. Missing artifacts must become explicit CLI errors.
