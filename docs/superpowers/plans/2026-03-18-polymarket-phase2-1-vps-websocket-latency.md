# Polymarket Phase 2.1 VPS And Low-Latency Market Data Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move paper trading onto a region-appropriate VPS, replace polling with a WebSocket-first market-data path, and add latency measurements so future strategy work is based on realistic live timing.

**Architecture:** Keep the existing engine and paper-only execution model, but upgrade the live boundary to use CLOB market WebSockets as the primary feed with REST snapshots only for bootstrap and recovery. Add an explicit latency-measurement layer plus deployment assets so the bot can run continuously on a remote host before any authenticated trading work begins.

**Tech Stack:** Python 3.9+, `httpx`, `websockets`, `typer`, `pytest`, `pytest-asyncio`, `systemd`

---

## Scope Check

This plan intentionally covers:

- VPS-oriented runtime configuration
- endpoint and region latency benchmarking
- public CLOB market WebSocket ingestion
- snapshot bootstrap plus streaming paper-trading mode
- latency and feed-health artifacts
- deployment runbook and `systemd` service assets

This plan does not include:

- authenticated order placement
- wallet signing or API credential generation
- autonomous live-money trading
- long-run reconnect hardening beyond the minimum needed to keep paper sessions usable

This phase should happen before serious strategy evaluation on live data, because the current polling path is too slow to tell whether missed opportunities are strategy failures or transport failures.

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add transport, WebSocket, RPC, and runtime artifact settings.
- Modify: `src/polymarket_arb/clients/clob.py`
  Add market-stream subscription and snapshot bootstrap helpers.
- Modify: `src/polymarket_arb/adapters/live.py`
  Support streaming-first event iteration with REST bootstrap and fallback recovery.
- Modify: `src/polymarket_arb/cli.py`
  Add latency benchmark and streaming paper-trading commands or flags.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Persist latency summaries and feed-health artifacts.
- Modify: `README.md`
  Document VPS setup, benchmark workflow, and streaming paper mode.

### Files To Create

- Create: `src/polymarket_arb/ops/latency.py`
  Shared latency benchmark helpers for HTTP and WebSocket endpoints.
- Create: `src/polymarket_arb/ops/deploy.py`
  Small helpers for runtime path validation and environment checks.
- Create: `tests/fixtures/clob/ws_market_book.json`
  Realistic market-channel book update fixture.
- Create: `tests/unit/ops/test_latency.py`
  Tests for percentile and summary calculations.
- Create: `tests/unit/clients/test_clob_market_ws.py`
  Tests for subscription payloads and WebSocket message normalization.
- Create: `tests/unit/adapters/test_live_streaming_phase2_1.py`
  Tests for snapshot bootstrap, streaming updates, and stale-feed handling.
- Create: `tests/integration/test_bench_latency_cli.py`
  CLI test for benchmark artifact output.
- Create: `tests/integration/test_run_paper_streaming_cli.py`
  CLI test for streaming paper mode.
- Create: `ops/systemd/polymarket-paper.service`
  Example service unit for VPS paper-trading sessions.
- Create: `ops/env/polymarket-paper.env.example`
  Example environment file template for remote deployment.

## Task 1: Add Runtime Transport Settings

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Modify: `configs/markets.sample.yaml`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path

from polymarket_arb.config import load_settings


def test_load_settings_reads_streaming_transport_and_runtime_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "streaming.yaml"
    config_path.write_text(
        """
        venue: polymarket
        api:
          gamma_base_url: https://gamma-api.polymarket.com
          clob_base_url: https://clob.polymarket.com
          market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
          poll_interval_ms: 500
        runtime:
          mode: stream
          artifact_dir: artifacts/runtime
          polygon_rpc_url: https://polygon-rpc.example
        markets:
          - slug: bitboy-convicted
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

    assert settings.api.market_ws_url.endswith("/ws/market")
    assert settings.runtime.mode == "stream"
    assert settings.runtime.artifact_dir == "artifacts/runtime"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py -v`
Expected: FAIL because WebSocket and runtime settings do not exist yet.

- [ ] **Step 3: Add minimal transport settings**

```python
class RuntimeSettings(BaseModel):
    mode: str = "poll"
    artifact_dir: str = "artifacts/runtime"
    polygon_rpc_url: str | None = None


class ApiSettings(BaseModel):
    gamma_base_url: str
    clob_base_url: str
    market_ws_url: str
    poll_interval_ms: int = Field(gt=0)
```

- [ ] **Step 4: Update `configs/markets.sample.yaml`**

```yaml
api:
  gamma_base_url: https://gamma-api.polymarket.com
  clob_base_url: https://clob.polymarket.com
  market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
  poll_interval_ms: 500
runtime:
  mode: stream
  artifact_dir: artifacts/runtime
  polygon_rpc_url: https://polygon-rpc.example
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/config.py configs/markets.sample.yaml tests/unit/test_config.py
git commit -m "feat: add streaming runtime settings"
```

## Task 2: Add Latency Benchmark Helpers And CLI

**Files:**
- Create: `src/polymarket_arb/ops/latency.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/unit/ops/test_latency.py`
- Create: `tests/integration/test_bench_latency_cli.py`

- [ ] **Step 1: Write the failing latency summary test**

```python
from polymarket_arb.ops.latency import summarize_samples


def test_summarize_samples_returns_basic_percentiles() -> None:
    summary = summarize_samples([8.0, 10.0, 12.0, 20.0, 30.0])

    assert summary["count"] == 5
    assert summary["p50_ms"] == 12.0
    assert summary["max_ms"] == 30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/ops/test_latency.py -v`
Expected: FAIL because no latency helper module exists.

- [ ] **Step 3: Add latency measurement helpers**

```python
def summarize_samples(samples_ms: list[float]) -> dict[str, float]:
    ...


def measure_http_endpoint(... ) -> list[float]:
    ...


async def measure_websocket_connect(... ) -> list[float]:
    ...
```

- [ ] **Step 4: Add a benchmark CLI command**

```python
@app.command("bench-latency")
def bench_latency(
    config_path: Path = typer.Option(..., "--config-path"),
    output_path: Path = typer.Option(..., "--output-path"),
    samples: int = typer.Option(10, "--samples"),
) -> None:
    ...
```

- [ ] **Step 5: Persist a benchmark artifact**

```json
{
  "gamma": {"p50_ms": 12.0},
  "clob_rest": {"p50_ms": 15.0},
  "market_ws_connect": {"p50_ms": 18.0}
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/ops/test_latency.py tests/integration/test_bench_latency_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/ops/latency.py src/polymarket_arb/cli.py tests/unit/ops/test_latency.py tests/integration/test_bench_latency_cli.py
git commit -m "feat: add latency benchmark command"
```

## Task 3: Add CLOB Market WebSocket Parsing

**Files:**
- Modify: `src/polymarket_arb/clients/clob.py`
- Create: `tests/fixtures/clob/ws_market_book.json`
- Create: `tests/unit/clients/test_clob_market_ws.py`

- [ ] **Step 1: Write the failing WebSocket parse test**

```python
import json
from pathlib import Path

from polymarket_arb.clients.clob import normalize_market_ws_message


def test_normalize_market_ws_message_extracts_book_update() -> None:
    payload = json.loads(Path("tests/fixtures/clob/ws_market_book.json").read_text())

    message = normalize_market_ws_message(payload)

    assert message.event_type == "book"
    assert message.asset_id == "yes-token-1"
    assert message.asks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob_market_ws.py -v`
Expected: FAIL because market-stream parsing does not exist.

- [ ] **Step 3: Add a minimal stream message model and parser**

```python
class ClobMarketStreamMessage(BaseModel):
    event_type: str
    asset_id: str | None = None
    asks: list[BookLevel] = Field(default_factory=list)
    timestamp_ms: int | None = None
```

```python
def normalize_market_ws_message(payload: dict[str, Any]) -> ClobMarketStreamMessage:
    ...
```

- [ ] **Step 4: Add subscription helper**

```python
def build_market_subscription(asset_ids: list[str]) -> dict[str, Any]:
    return {"asset_ids": asset_ids, "type": "market"}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob_market_ws.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/clients/clob.py tests/fixtures/clob/ws_market_book.json tests/unit/clients/test_clob_market_ws.py
git commit -m "feat: add clob market websocket parsing"
```

## Task 4: Add Streaming-First Live Adapter

**Files:**
- Modify: `src/polymarket_arb/adapters/live.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/unit/adapters/test_live_streaming_phase2_1.py`
- Create: `tests/integration/test_run_paper_streaming_cli.py`

- [ ] **Step 1: Write the failing streaming adapter test**

```python
from polymarket_arb.adapters.live import LiveAdapter


def test_live_adapter_bootstraps_books_then_emits_stream_updates() -> None:
    ...
    events = list(adapter.iter_events(limit_seconds=0))

    assert events[0].side == "YES"
    assert events[-1].timestamp_ms >= events[0].timestamp_ms
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/adapters/test_live_streaming_phase2_1.py -v`
Expected: FAIL because the adapter only polls REST books.

- [ ] **Step 3: Add snapshot bootstrap plus stream path**

```python
class LiveAdapter:
    def iter_streaming_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        yield from self._bootstrap_snapshot_events()
        async for message in self._clob_ws_client.subscribe(...):
            ...
```

- [ ] **Step 4: Keep polling mode available**

```python
def iter_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
    if self._runtime_mode == "stream":
        yield from self.iter_streaming_events(limit_seconds)
    else:
        yield from self.iter_polling_events(limit_seconds)
```

- [ ] **Step 5: Add a streaming paper-run path to CLI**

```python
@app.command("run-paper")
def run_paper(..., mode: str = typer.Option("stream", "--mode")) -> None:
    ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/adapters/test_live_streaming_phase2_1.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/adapters/live.py src/polymarket_arb/cli.py tests/unit/adapters/test_live_streaming_phase2_1.py tests/integration/test_run_paper_streaming_cli.py
git commit -m "feat: add streaming paper trading mode"
```

## Task 5: Add Feed-Health And Latency Artifacts

**Files:**
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `src/polymarket_arb/ops/deploy.py`
- Test: `tests/integration/test_bench_latency_cli.py`

- [ ] **Step 1: Write the failing artifact test**

```python
from pathlib import Path

from polymarket_arb.reporting.writers import write_latency_summary


def test_write_latency_summary_creates_json_artifact(tmp_path: Path) -> None:
    target = tmp_path / "latency.json"

    write_latency_summary(target, {"gamma": {"p50_ms": 10.0}})

    assert target.exists()
    assert '"gamma"' in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_bench_latency_cli.py -v`
Expected: FAIL because no dedicated latency artifact writer exists.

- [ ] **Step 3: Add artifact and runtime-path helpers**

```python
def write_latency_summary(path: Path, payload: dict[str, Any]) -> None:
    ...


def ensure_runtime_paths(... ) -> None:
    ...
```

- [ ] **Step 4: Emit feed-health summary after paper sessions**

```python
{
  "mode": "stream",
  "events_seen": 1234,
  "stale_feed_events": 0,
  "reconnects": 1
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_bench_latency_cli.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/reporting/writers.py src/polymarket_arb/ops/deploy.py tests/integration/test_bench_latency_cli.py tests/integration/test_run_paper_streaming_cli.py
git commit -m "feat: add latency and feed health artifacts"
```

## Task 6: Add VPS Deployment Assets And Verification Docs

**Files:**
- Create: `ops/systemd/polymarket-paper.service`
- Create: `ops/env/polymarket-paper.env.example`
- Modify: `README.md`

- [ ] **Step 1: Add a `systemd` unit template**

```ini
[Unit]
Description=Polymarket paper trader
After=network-online.target

[Service]
WorkingDirectory=/srv/polymarket-bot
EnvironmentFile=/srv/polymarket-bot/ops/env/polymarket-paper.env
ExecStart=/srv/polymarket-bot/.venv/bin/python -m polymarket_arb.cli run-paper --config-path /srv/polymarket-bot/configs/markets.sample.yaml --output-dir /srv/polymarket-bot/artifacts/paper-report --mode stream
Restart=always

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Add an environment file example**

```bash
POLYMARKET_CONFIG_PATH=/srv/polymarket-bot/configs/markets.sample.yaml
POLYGON_RPC_URL=https://polygon-rpc.example
```

- [ ] **Step 3: Update README with VPS workflow**

```markdown
1. Run `bench-latency` on each candidate VPS.
2. Pick the lowest-latency non-blocked region.
3. Start `run-paper --mode stream` under `systemd`.
4. Review latency and feed-health artifacts before moving on.
```

- [ ] **Step 4: Run the focused verification commands**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/ops/test_latency.py tests/unit/clients/test_clob_market_ws.py tests/unit/adapters/test_live_streaming_phase2_1.py tests/integration/test_bench_latency_cli.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: PASS

Run: `PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli bench-latency --help`
Expected: shows config, output path, and samples options

Run: `PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --help`
Expected: shows streaming mode option

- [ ] **Step 5: Commit**

```bash
git add ops/systemd/polymarket-paper.service ops/env/polymarket-paper.env.example README.md
git commit -m "docs: add vps streaming deployment workflow"
```

## Notes For The Implementer

- Keep this phase paper-only. Any real order placement still belongs in Phase 6.
- Treat REST orderbook reads as bootstrap and recovery helpers, not the primary live feed.
- Choose the VPS region by benchmark evidence from `bench-latency`, not by provider marketing claims.
- Keep Phase 4 focused on resilience improvements that remain after this first-cut low-latency migration.
