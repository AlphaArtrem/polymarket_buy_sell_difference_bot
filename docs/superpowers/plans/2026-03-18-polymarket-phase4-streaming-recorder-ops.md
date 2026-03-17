# Polymarket Phase 4 Streaming Recorder And Live Ops Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the short-lived polling-only live path with a resilient streaming recorder and paper-trading adapter suitable for longer operational sessions.

**Architecture:** Keep the normalized event model introduced in earlier phases, but upgrade the live boundary to combine initial snapshots with streaming deltas, explicit freshness tracking, reconnect logic, and long-run recorder metadata. Polling remains as a fallback path, not the primary one.

**Tech Stack:** Python 3.9+, `httpx`, `websockets`, `typer`, `pytest`, `pytest-asyncio`

---

## Scope Check

This plan intentionally covers:

- public WebSocket ingestion
- reconnect and stale-data handling
- recorder run metadata and health logging
- long-lived paper sessions on real streams

This plan does not include:

- authenticated order placement
- deployment daemons or service managers
- cross-market alpha logic

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/clients/clob.py`
  Add streaming subscription helpers and message normalization.
- Modify: `src/polymarket_arb/adapters/live.py`
  Support snapshot bootstrapping plus streaming deltas and fallback polling.
- Modify: `src/polymarket_arb/domain/events.py`
  Expand event types for heartbeat, disconnect, and snapshot-origin flags if needed.
- Modify: `src/polymarket_arb/state/store.py`
  Support delta updates and stronger freshness checks.
- Modify: `src/polymarket_arb/recording/recorder.py`
  Write run metadata and health/heartbeat records.
- Modify: `src/polymarket_arb/recording/storage.py`
  Persist metadata and separate event channels cleanly.
- Modify: `src/polymarket_arb/cli.py`
  Add flags for streaming vs polling mode and longer session controls.
- Modify: `README.md`
  Document long-running capture usage and operational caveats.

### Files To Create

- Create: `tests/fixtures/clob/ws_book_event.json`
  Realistic streaming message fixture for one side of a book.
- Create: `tests/fixtures/clob/ws_trade_event.json`
  Realistic message fixture for non-book data that should be ignored or routed separately.
- Create: `tests/unit/clients/test_clob_ws.py`
  Tests for message parsing and channel subscription payloads.
- Create: `tests/unit/adapters/test_live_streaming.py`
  Tests for snapshot bootstrap, delta application, and fallback behavior.
- Create: `tests/unit/recording/test_run_metadata.py`
  Tests for metadata and heartbeat persistence.
- Create: `tests/integration/test_record_live_streaming_cli.py`
  End-to-end streaming record-live CLI test with mocked WebSocket and snapshot clients.
- Create: `tests/integration/test_run_paper_streaming_cli.py`
  End-to-end streaming paper session test.

## Task 1: Add WebSocket Message Parsing And Subscription Helpers

**Files:**
- Modify: `src/polymarket_arb/clients/clob.py`
- Create: `tests/fixtures/clob/ws_book_event.json`
- Create: `tests/fixtures/clob/ws_trade_event.json`
- Create: `tests/unit/clients/test_clob_ws.py`

- [ ] **Step 1: Write the failing streaming parse test**

```python
import json
from pathlib import Path

from polymarket_arb.clients.clob import normalize_ws_message


def test_normalize_ws_message_extracts_book_update() -> None:
    payload = json.loads(Path("tests/fixtures/clob/ws_book_event.json").read_text())

    message = normalize_ws_message(payload)

    assert message.event_type == "book"
    assert message.asset_id
    assert message.asks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob_ws.py -v`
Expected: FAIL because no WebSocket normalization exists.

- [ ] **Step 3: Add minimal message models and parser**

```python
class ClobStreamMessage(BaseModel):
    event_type: str
    asset_id: str | None = None
    asks: list[BookLevel] = Field(default_factory=list)
    timestamp_ms: int | None = None
```

```python
def normalize_ws_message(payload: dict[str, Any]) -> ClobStreamMessage:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob_ws.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_arb/clients/clob.py tests/fixtures/clob/ws_book_event.json tests/fixtures/clob/ws_trade_event.json tests/unit/clients/test_clob_ws.py
git commit -m "feat: add clob websocket message parsing"
```

## Task 2: Bootstrap Live State With Snapshot Plus Delta Updates

**Files:**
- Modify: `src/polymarket_arb/adapters/live.py`
- Modify: `src/polymarket_arb/state/store.py`
- Create: `tests/unit/adapters/test_live_streaming.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
from polymarket_arb.adapters.live import LiveAdapter


def test_live_adapter_bootstraps_from_snapshot_then_applies_deltas() -> None:
    ...
    events = list(adapter.iter_events(limit_seconds=0))

    assert events[0].side == "YES"
    assert events[-1].timestamp_ms > events[0].timestamp_ms
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/adapters/test_live_streaming.py -v`
Expected: FAIL because the adapter only polls bulk books.

- [ ] **Step 3: Add a streaming bootstrap path**

```python
class LiveAdapter:
    def iter_streaming_events(self, limit_seconds: int = 60) -> Iterable[OrderBookEvent]:
        snapshots = self._clob_client.fetch_order_books(token_ids)
        for event in snapshot_events:
            yield event
        async for message in self._clob_ws_client.subscribe(...):
            ...
```

- [ ] **Step 4: Preserve polling as fallback**

```python
if self._mode == "poll":
    yield from self.iter_polling_events(limit_seconds)
else:
    yield from self.iter_streaming_events(limit_seconds)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/adapters/test_live_streaming.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/adapters/live.py src/polymarket_arb/state/store.py tests/unit/adapters/test_live_streaming.py
git commit -m "feat: add streaming live adapter bootstrap"
```

## Task 3: Add Reconnect, Freshness, And Recorder Metadata

**Files:**
- Modify: `src/polymarket_arb/domain/events.py`
- Modify: `src/polymarket_arb/recording/recorder.py`
- Modify: `src/polymarket_arb/recording/storage.py`
- Create: `tests/unit/recording/test_run_metadata.py`

- [ ] **Step 1: Write the failing metadata test**

```python
from polymarket_arb.recording.recorder import Recorder
from polymarket_arb.recording.storage import JsonlEventStore


def test_recorder_writes_run_metadata_and_heartbeat(tmp_path) -> None:
    store = JsonlEventStore(tmp_path)
    recorder = Recorder(store)

    recorder.start_run(catalog=[], mode="stream")
    recorder.record_heartbeat(timestamp_ms=1000, message="connected")

    metadata = store.read_run_metadata()
    assert metadata["mode"] == "stream"
    assert metadata["heartbeats"][0]["message"] == "connected"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/recording/test_run_metadata.py -v`
Expected: FAIL because recorder metadata is not persisted.

- [ ] **Step 3: Add metadata helpers**

```python
def write_run_metadata(self, metadata: dict[str, Any]) -> None:
    ...

def append_heartbeat(self, payload: dict[str, Any]) -> None:
    ...
```

- [ ] **Step 4: Update `Recorder` to use them**

```python
def start_run(self, catalog: list[MarketCatalogEntry], mode: str) -> None:
    ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/recording/test_run_metadata.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/domain/events.py src/polymarket_arb/recording/recorder.py src/polymarket_arb/recording/storage.py tests/unit/recording/test_run_metadata.py
git commit -m "feat: add run metadata and heartbeat persistence"
```

## Task 4: Wire Streaming CLI Paths And Long-Session Controls

**Files:**
- Modify: `src/polymarket_arb/cli.py`
- Modify: `README.md`
- Create: `tests/integration/test_record_live_streaming_cli.py`
- Create: `tests/integration/test_run_paper_streaming_cli.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_record_live_accepts_stream_mode_flag(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["record-live", "--config-path", "...", "--run-dir", "...", "--mode", "stream"],
    )
    assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_record_live_streaming_cli.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: FAIL because the CLI does not expose stream/poll modes.

- [ ] **Step 3: Add CLI flags**

```python
mode: str = typer.Option("stream", "--mode")
max_disconnect_seconds: int = typer.Option(15, "--max-disconnect-seconds")
```

- [ ] **Step 4: Wire those flags to the live adapter**

```python
adapter = build_live_adapter(settings, catalog, mode=mode, max_disconnect_seconds=max_disconnect_seconds)
```

- [ ] **Step 5: Document operational usage**

```markdown
Use `--mode stream` for production-like capture and `--mode poll` as a fallback.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_record_live_streaming_cli.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/cli.py README.md tests/integration/test_record_live_streaming_cli.py tests/integration/test_run_paper_streaming_cli.py
git commit -m "feat: add streaming cli mode"
```

## Task 5: Verify The Full Phase

- [ ] **Step 1: Run focused verification**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_clob_ws.py tests/unit/adapters/test_live_streaming.py tests/unit/recording/test_run_metadata.py tests/integration/test_record_live_streaming_cli.py tests/integration/test_run_paper_streaming_cli.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 3: Commit any final README adjustments**

```bash
git add README.md
git commit -m "docs: describe streaming live mode"
```
